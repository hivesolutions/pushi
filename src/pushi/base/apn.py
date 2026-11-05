#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (c) 2008-2024 Hive Solutions Lda.
#
# This file is part of Hive Pushi System.
#
# Hive Pushi System is free software: you can redistribute it and/or modify
# it under the terms of the Apache License as published by the Apache
# Foundation, either version 2.0 of the License, or (at your option) any
# later version.
#
# Hive Pushi System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# Apache License for more details.
#
# You should have received a copy of the Apache License along with
# Hive Pushi System. If not, see <http://www.apache.org/licenses/>.

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os
import json
import time
import base64
import shutil
import binascii
import tempfile

import appier

import netius.clients

import pushi

from . import handler

try:
    import httpx
except ImportError:
    httpx = None

try:
    import cryptography.hazmat.primitives.hashes
    import cryptography.hazmat.primitives.serialization
    import cryptography.hazmat.primitives.asymmetric.ec
    import cryptography.hazmat.primitives.asymmetric.utils
except ImportError:
    cryptography = None

HOST = "api.push.apple.com"
""" The host of the (HTTP/2 based) APN provider API to be used
for the production environment """

SANDBOX_HOST = "api.sandbox.push.apple.com"
""" The host of the (HTTP/2 based) APN provider API to be used
for the sandbox (development) environment """

TOKEN_TTL = 3000
""" The time (in seconds) during which a provider (JWT) token is
re-used before a new one is generated, note that Apple rejects
tokens older than one hour and refuses refreshes more frequent than
once every twenty minutes, so fifty minutes are used """

TIMEOUT = 30.0
""" The timeout (in seconds) to be used in the requests sent to
the APN provider API, avoids hanging forever on a stale connection """

INVALID_REASONS = ("BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic")
""" The set of reasons returned by the APN provider API for which
the device token is considered to be no longer valid, meaning that
its subscriptions should be removed """

EXPIRED_REASONS = ("ExpiredProviderToken", "InvalidProviderToken")
""" The set of reasons returned by the APN provider API for which
the provider (JWT) token should be generated again """


class APNHandler(handler.Handler):
    """
    Pushi handler (adapter) for the Apple Push Notifications
    (APN) infra-structure, so that it's possible to send
    push notification to iOS/OSX devices.

    Notifications are sent using the HTTP/2 based APN provider
    API, authenticated either with a provider (JWT) token signed
    with a .p8 key (token based) or with a certificate, falling
    back to the legacy binary protocol (certificate only) in case
    no HTTP/2 client is available.

    :see: https://developer.apple.com/documentation/usernotifications
    """

    def __init__(self, owner):
        handler.Handler.__init__(self, owner, name="apn")
        self.subs = {}
        self.provider_tokens = {}

    def send(self, app_id, event, json_d, invalid={}):
        # tries to retrieve the appropriate message starting from
        # the most general values to the most specific values,
        # be aware that the value may be a bit fuzzy
        message = json_d.get("data", None)
        message = json_d.get("push", message)
        message = json_d.get("apn", message)
        if not message:
            raise RuntimeError("No message defined")

        # retrieves the reference to the app with the defined app id
        app = self.owner.get_app(app_id=app_id)

        # retrieves the app key for the retrieved app by unpacking the current
        # app structure into the appropriate values
        app_key = app.key

        # saves the original event name for the received event, so that it may
        # be used latter for debugging/log purposes
        root_event = event

        # resolves the complete set of (extra) channels for the provided
        # event assuming that it may be associated with alias, then creates
        # the complete list of event containing also the "extra" events
        extra = self.owner.get_channels(app_key, event)
        events = [event] + extra

        # retrieves the complete set of subscriptions for the current APN
        # infra-structure to be able to resolve the appropriate tokens
        subs = self.subs.get(app_id, {})

        # creates the initial list of tokens to be notified and then populates
        # the list with the various token associated with the complete set of
        # resolved events, note that a set is created at the end so that one
        # token gets notified only once (no double notifications)
        tokens = []
        for event in events:
            _tokens = subs.get(event, [])
            tokens.extend(_tokens)
        tokens = set(tokens)
        count = len(tokens)

        # prints a logging message about the various (web) subscriptions
        # that were found for the event that was triggered
        self.logger.debug("Found %d APN subscription(s) for '%s'" % (count, root_event))

        # delegates to the direct send method with resolved tokens
        self.send_to_tokens(tokens, message, app=app, invalid=invalid)

    def send_to_tokens(
        self,
        tokens,
        message,
        app=None,
        key_data=None,
        cer_data=None,
        sandbox=None,
        invalid=None,
        auth_key=None,
        key_id=None,
        team_id=None,
        topic=None,
        **kwargs
    ):
        """
        Sends APN notifications directly to a set of device tokens.

        This method can be used for direct messaging without requiring
        pub/sub subscriptions, while reusing the core sending logic.

        In case an authentication (.p8) key is available the token
        based authentication is used, otherwise the certificate based
        one (key and certificate) is used instead.

        :type tokens: List/Set
        :param tokens: Device tokens to send to.
        :type message: Dictionary/String
        :param message: Notification payload with APN fields.
        :type app: App
        :param app: Optional App instance for credentials.
        :type key_data: String
        :param key_data: PEM-encoded private key (overrides app).
        :type cer_data: String
        :param cer_data: PEM-encoded certificate (overrides app).
        :type sandbox: bool
        :param sandbox: Use sandbox environment (overrides app).
        :type invalid: Dictionary
        :param invalid: Map of already sent tokens to skip (updated in place).
        :type auth_key: String
        :param auth_key: PEM-encoded (.p8) authentication key for the
        token based authentication (overrides app).
        :type key_id: String
        :param key_id: Identifier of the authentication key (overrides app).
        :type team_id: String
        :param team_id: Identifier of the Apple Developer team (overrides app).
        :type topic: String
        :param topic: Topic (bundle identifier) of the target application,
        required for the token based authentication (overrides app).
        :rtype: Dictionary
        :return: Result with success status and sent tokens.
        """

        # creates a new map of invalid (already sent) items in case none
        # is provided, a shared default map would make tokens that were
        # notified once be skipped in every following direct send
        if invalid == None:
            invalid = dict()

        # retrieves the APN specific values from the app to be used in
        # the process of authentication, can be overridden by direct params
        if app:
            key_data = key_data or getattr(app, "apn_key", None)
            cer_data = cer_data or getattr(app, "apn_cer", None)
            auth_key = auth_key or getattr(app, "apn_auth_key", None)
            key_id = key_id or getattr(app, "apn_key_id", None)
            team_id = team_id or getattr(app, "apn_team_id", None)
            topic = topic or getattr(app, "apn_topic", None)
            if sandbox == None:
                sandbox = getattr(app, "apn_sandbox", False)

        if sandbox == None:
            sandbox = False

        # in case no message or no valid set of credentials (either the
        # token or the certificate based ones) is present a runtime error
        # is raised to indicate the problem
        if not message:
            raise RuntimeError("No message defined")
        if auth_key:
            if not key_id:
                raise RuntimeError("No APN key id defined")
            if not team_id:
                raise RuntimeError("No APN team id defined")
            if not topic:
                raise RuntimeError("No APN topic defined")
        else:
            if not key_data:
                raise RuntimeError("No APN key defined")
            if not cer_data:
                raise RuntimeError("No APN certificate defined")

        # normalizes tokens to a set for iteration, ensuring that
        # one token gets notified only once (no double notifications)
        if type(tokens) in appier.legacy.STRINGS:
            tokens = [tokens]
        tokens = set(tokens)

        if not tokens:
            return dict(success=True, tokens=[])

        # in case the token based authentication is to be used sends the
        # notifications through the HTTP/2 provider API, authenticated with
        # a provider (JWT) token signed with the authentication key
        if auth_key:
            if not httpx:
                raise RuntimeError("httpx library not available, required for APN")
            if not cryptography:
                raise RuntimeError(
                    "cryptography library not available, required for APN"
                )
            return self.send_h2(
                tokens,
                message,
                sandbox=sandbox,
                topic=topic,
                invalid=invalid,
                auth=lambda force=False: self.provider_token(
                    auth_key, key_id, team_id, force=force
                ),
            )

        # ensures that the complete set of data is encoded as bytes, as
        # this is required for the proper writing of the file, otherwise
        # an invalid encoding would be raised for some platforms
        key_data = netius.legacy.bytes(key_data)
        cer_data = netius.legacy.bytes(cer_data)

        # creates a new temporary directory that will be used to store
        # the temporary key and certificate files for SSL
        path = tempfile.mkdtemp()

        # creates the full paths to both the key and certificate
        # files using the temporary path as base
        key_path = os.path.join(path, "apn.key")
        cer_path = os.path.join(path, "apn.cer")

        # opens the SSL key file for writing (in binary mode) and
        # then writes the current data into it so that it may be
        # used by the encryption infra-structure
        key_file = open(key_path, "wb")
        try:
            key_file.write(key_data)
        finally:
            key_file.close()

        # opens the temporary certificate file and writes
        # the retrieved certificate data into it, to be used
        # temporarily by the SSL infra-structure
        cer_file = open(cer_path, "wb")
        try:
            cer_file.write(cer_data)
        finally:
            cer_file.close()

        # in case the HTTP/2 client is available sends the notifications
        # through the provider API using the certificate for the client
        # authentication, removing the temporary files at the end
        if httpx:
            try:
                return self.send_h2(
                    tokens,
                    message,
                    sandbox=sandbox,
                    topic=topic,
                    invalid=invalid,
                    cert=(cer_path, key_path),
                )
            finally:
                self.logger.debug("Removing temporary APN keys")
                shutil.rmtree(path, ignore_errors=True)

        # creates the counter that will be used by the cleanup function
        # to know exactly when to remove the SSL associated files
        pending = len(tokens)
        clojure = dict(pending=pending)
        sent_tokens = []

        # creates the cleanup function that will be called for
        # the close operation of the APN protocol, this function
        # will remove the temporary path when called as a response
        # to the "stop" of the last protocol
        def cleanup(protocol):
            # schedules the stop of the current event loop as the
            # APN operation has been completed with success
            netius.compat_loop(loop).stop()

            # retrieves the number of pending APN messages from the
            # clojure and verifies if the end has been reached
            pending = clojure["pending"]
            pending -= 1
            clojure["pending"] = pending
            if not pending == 0:
                return

            # removes the temporary keys and certificate files as
            # they are no longer required for APN usage
            self.logger.debug("Removing temporary APN keys")
            shutil.rmtree(path, ignore_errors=True)

        # iterates over the complete set of tokens to be notified and notifies
        # them using the current APN client infra-structure
        for token in tokens:
            # in case the current token is present in the current
            # map of invalid items must skip iteration as the message
            # has probably already been sent "to the token"
            if token in invalid:
                continue

            # prints a debug message about the APN message that
            # is going to be sent (includes token)
            self.logger.debug("Sending APN message to '%s'" % token)

            # creates the new APN protocol to be used and uses it to
            # send the new message (should be correctly serialized)
            loop, protocol = netius.clients.APNClient.notify_s(
                token,
                message=message,
                sandbox=sandbox,
                key_file=key_path,
                cer_file=cer_path,
            )
            protocol.bind("finish", cleanup)
            loop.run_forever()

            # adds the current token to the list of invalid items for
            # the current message sending stream
            invalid[token] = True
            sent_tokens.append(token)

        return dict(success=True, tokens=sent_tokens)

    def send_h2(
        self,
        tokens,
        message,
        sandbox=False,
        topic=None,
        invalid=None,
        auth=None,
        cert=None,
    ):
        """
        Sends APN notifications to a set of device tokens using the
        HTTP/2 based APN provider API.

        Device tokens reported by the provider API as no longer valid
        have their subscriptions removed, and a provider token reported
        as expired (or invalid) is generated again and the notification
        retried once.

        :type tokens: List/Set
        :param tokens: Device tokens to send to.
        :type message: Dictionary/String
        :param message: Notification payload with APN fields.
        :type sandbox: bool
        :param sandbox: Use sandbox environment.
        :type topic: String
        :param topic: Topic (bundle identifier) of the target application.
        :type invalid: Dictionary
        :param invalid: Map of already sent tokens to skip (updated in place).
        :type auth: Function
        :param auth: Function that returns the provider (JWT) token for
        the token based authentication, called with `force` set to request
        a new token (unset for the certificate based authentication).
        :type cert: Tuple
        :param cert: Paths to the certificate and to the key files for the
        certificate based authentication (unset for the token based one).
        :rtype: Dictionary
        :return: Result with success status and sent tokens.
        """

        # creates a new map of invalid (already sent) items in case none
        # is provided, so that each send operation starts clean
        if invalid == None:
            invalid = dict()

        # resolves the host to be used according to the environment and
        # builds both the payload and the base headers of the request
        host = SANDBOX_HOST if sandbox else HOST
        payload = self._payload(message)
        headers = {"apns-push-type": "alert", "apns-priority": "10"}
        if topic:
            headers["apns-topic"] = topic

        sent_tokens = []

        # creates the HTTP/2 client that is going to be re-used for the
        # complete set of notifications (single connection to the API)
        client = httpx.Client(http2=True, cert=cert, timeout=TIMEOUT)

        try:
            # iterates over the complete set of tokens to be notified and
            # notifies them using the provider API
            for token in tokens:
                # in case the current token is present in the current
                # map of invalid items must skip iteration as the message
                # has probably already been sent "to the token"
                if token in invalid:
                    continue

                # prints a debug message about the APN message that
                # is going to be sent (includes token)
                self.logger.debug("Sending APN message to '%s'" % token)

                url = "https://%s/3/device/%s" % (host, token)
                force = False

                # tries to send the notification at most twice, so that a
                # provider token rejected as expired is generated again
                for _index in range(2):
                    if auth:
                        headers["authorization"] = "bearer %s" % auth(force=force)

                    try:
                        response = client.post(url, content=payload, headers=headers)
                    except Exception as exception:
                        self.logger.warning(
                            "Failed to send APN message to '%s': %s"
                            % (token, str(exception))
                        )
                        break

                    if response.status_code == 200:
                        # adds the current token to the list of invalid items
                        # for the current message sending stream
                        invalid[token] = True
                        sent_tokens.append(token)
                        break

                    reason = self._reason(response)
                    self.logger.warning(
                        "Failed to send APN message to '%s' (%d): %s"
                        % (token, response.status_code, reason)
                    )

                    # in case the provider token has expired (or is invalid)
                    # retries the notification with a new provider token
                    if auth and not force and reason in EXPIRED_REASONS:
                        force = True
                        continue

                    # in case the device token is no longer valid (eg: the
                    # app has been removed from the device) removes the
                    # complete set of subscriptions associated with it
                    if response.status_code == 410 or reason in INVALID_REASONS:
                        self.logger.info("APN token no longer valid: '%s'" % token)
                        try:
                            self.unsubscribes(token)
                        except Exception:
                            pass

                    break
        finally:
            client.close()

        return dict(success=True, tokens=sent_tokens)

    def provider_token(self, auth_key, key_id, team_id, force=False):
        """
        Retrieves the provider (JWT) token to be used for the token
        based authentication against the APN provider API, re-using
        the previously generated one while it's still valid.

        The token is signed using ES256 with the authentication key,
        identified by the key identifier (`kid`) and issued by the team
        identifier (`iss`).

        :type auth_key: String
        :param auth_key: PEM-encoded (.p8) authentication key.
        :type key_id: String
        :param key_id: Identifier of the authentication key.
        :type team_id: String
        :param team_id: Identifier of the Apple Developer team.
        :type force: bool
        :param force: If a new token should be generated even if the
        previous one is still valid.
        :rtype: String
        :return: The provider (JWT) token.
        """

        # tries to re-use the previously generated token for the key, as
        # Apple refuses tokens that are refreshed too frequently
        current = int(time.time())
        cache_key = (team_id, key_id)
        provider_token = self.provider_tokens.get(cache_key, None)
        if provider_token and not force:
            token, issued = provider_token
            if current - issued < TOKEN_TTL:
                return token

        # builds the (base64 encoded) header and claims segments of the
        # token that are going to be signed (signing input)
        header = dict(alg="ES256", kid=key_id)
        claims = dict(iss=team_id, iat=current)
        signing_input = "%s.%s" % (
            self._base64(json.dumps(header)),
            self._base64(json.dumps(claims)),
        )

        # loads the authentication key and signs the input with it, converting
        # the DER encoded signature into the raw (r and s) format of JWS
        private_key = cryptography.hazmat.primitives.serialization.load_pem_private_key(
            appier.legacy.bytes(auth_key), password=None
        )
        signature = private_key.sign(
            appier.legacy.bytes(signing_input),
            cryptography.hazmat.primitives.asymmetric.ec.ECDSA(
                cryptography.hazmat.primitives.hashes.SHA256()
            ),
        )
        r, s = cryptography.hazmat.primitives.asymmetric.utils.decode_dss_signature(
            signature
        )
        signature = binascii.unhexlify("%064x%064x" % (r, s))

        # builds the final token and stores it for re-use
        token = "%s.%s" % (signing_input, self._base64(signature))
        self.provider_tokens[cache_key] = (token, current)
        return token

    def load(self):
        subs = pushi.APN.find()
        for sub in subs:
            app_id = sub.app_id
            token = sub.token
            event = sub.event
            self.add(app_id, token, event)

    def add(self, app_id, token, event):
        events = self.subs.get(app_id, {})
        tokens = events.get(event, [])
        tokens.append(token)
        events[event] = tokens
        self.subs[app_id] = events

    def remove(self, app_id, token, event):
        events = self.subs.get(app_id, {})
        tokens = events.get(event, [])
        if token in tokens:
            tokens.remove(token)

    def subscriptions(self, token=None, event=None):
        filter = dict()
        if token:
            filter["token"] = token
        if event:
            filter["event"] = event
        subscriptions = pushi.APN.find(map=True, **filter)
        return dict(subscriptions=subscriptions)

    def subscribe(self, apn, auth=None, unsubscribe=True):
        self.logger.debug("Subscribing '%s' for '%s'" % (apn.token, apn.event))

        is_private = (
            apn.event.startswith("private-")
            or apn.event.startswith("presence-")
            or apn.event.startswith("peer-")
            or apn.event.startswith("personal-")
        )

        if is_private:
            self.owner.verify(apn.app_key, apn.token, apn.event, auth)
        if unsubscribe:
            self.unsubscribe(apn.token, force=False)

        exists = pushi.APN.exists(token=apn.token, event=apn.event)
        if exists:
            apn = exists
        else:
            apn.save()

        self.logger.debug("Subscribed '%s' for '%s'" % (apn.token, apn.event))

        return apn

    def unsubscribe(self, token, event=None, force=True):
        self.logger.debug("Unsubscribing '%s' from '%s'" % (token, event or "*"))

        kwargs = dict(token=token, raise_e=force)
        if event:
            kwargs["event"] = event

        apn = pushi.APN.get(**kwargs)
        if not apn:
            return None

        apn.delete()

        self.logger.debug("Unsubscribed '%s' for '%s'" % (token, event or "*"))

        return apn

    def unsubscribes(self, token, event=None):
        kwargs = dict(token=token)
        if event:
            kwargs["event"] = event

        apns = pushi.APN.find(**kwargs)
        for apn in apns:
            apn.delete()

        return apns

    def _payload(self, message):
        """
        Builds the (JSON encoded) payload of the notification from the
        provided message, using it directly in case it's already a complete
        APN payload (contains the `aps` dictionary) or using it as the alert
        of a new payload otherwise (same as the legacy binary protocol).

        :type message: Dictionary/String
        :param message: Notification message or complete APN payload.
        :rtype: String
        :return: The JSON encoded payload as bytes.
        """

        if isinstance(message, dict) and "aps" in message:
            data = message
        else:
            data = dict(aps=dict(alert=message, sound="default", badge=0))
        return appier.legacy.bytes(json.dumps(data))

    def _reason(self, response):
        """
        Retrieves the reason of the failure from the response returned
        by the APN provider API, falling back to the response text in case
        the body is not a valid JSON error structure.

        :type response: Response
        :param response: The (failed) response from the provider API.
        :rtype: String
        :return: The reason of the failure (eg: `BadDeviceToken`).
        """

        try:
            return response.json().get("reason", None) or response.text
        except Exception:
            return response.text

    def _base64(self, data):
        """
        Encodes the provided data using the URL safe base64 variant
        without padding, as required by the JWS (JWT) specification.

        :type data: String
        :param data: The data (string or bytes) to be encoded.
        :rtype: String
        :return: The encoded data without padding.
        """

        data = base64.urlsafe_b64encode(appier.legacy.bytes(data))
        return data.rstrip(b"=").decode("utf-8")
