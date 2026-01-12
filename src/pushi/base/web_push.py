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

import json
import base64

import appier

import pushi

from . import handler

try:
    import pywebpush
except ImportError:
    pywebpush = None

try:
    import cryptography.hazmat.primitives.serialization
except ImportError:
    cryptography = None


class WebPushHandler(handler.Handler):
    """
    Event handler for W3C Web Push API notifications.

    This handler provides support for sending push notifications
    to web browsers using the Web Push protocol (RFC 8030).

    Notifications are sent using VAPID authentication and require
    subscription objects containing endpoint, p256dh key, and auth key.

    :see: https://w3c.github.io/push-api
    """

    def __init__(self, owner):
        handler.Handler.__init__(self, owner, name="web_push")
        self.subs = {}

    def send(self, app_id, event, json_d, invalid={}):
        """
        Sends Web Push notifications to all subscribed endpoints for
        the provided event/channel.

        Uses the pywebpush library to send encrypted notifications
        via the W3C Web Push protocol with VAPID authentication.
        Automatically removes expired/invalid subscriptions.

        :type app_id: String
        :param app_id: The application identifier for which the
        message is being sent.
        :type event: String
        :param event: The event/channel name to send the notification to.
        :type json_d: Dictionary
        :param json_d: The JSON data structure containing the notification
        payload and metadata.
        :type invalid: Dictionary
        :param invalid: Map of already processed subscription IDs to avoid
        duplicate sends (default: empty dict).
        """

        # verifies if the pywebpush library is available
        if not pywebpush:
            self.logger.warning(
                "pywebpush library not available, skipping Web Push notifications"
            )
            return

        # verifies if the cryptography library is available
        if not cryptography:
            self.logger.warning(
                "cryptography library not available, skipping Web Push notifications"
            )
            return

        # retrieves the reference to the app structure associated with the
        # id for which the message is being sent
        app = self.owner.get_app(app_id=app_id)

        # retrieves the app key for the retrieved app
        app_key = app.key

        # saves the original event name for debugging
        root_event = event

        # tries to extract the message from the JSON data structure
        message = json_d.get("data", None)
        message = json_d.get("push", message)
        message = json_d.get("web_push", message)
        message = json_d.get("message", message)

        # resolves the complete set of (extra) channels for the event
        extra = self.owner.get_channels(app_key, event)
        events = [event] + extra

        # retrieves the complete set of subscriptions
        subs = self.subs.get(app_id, {})

        # creates the list of subscription IDs to be notified
        subscription_ids = []
        for event in events:
            _subscriptions = subs.get(event, [])
            subscription_ids.extend(_subscriptions)
        subscription_ids = list(set(subscription_ids))
        count = len(subscription_ids)

        self.logger.debug(
            "Found %d Web Push subscription(s) for '%s'" % (count, root_event)
        )

        # batch fetch all subscription objects from the database
        subscription_ids_to_fetch = [
            sid for sid in subscription_ids if sid not in invalid
        ]
        subscription_objects = pushi.WebPush.find(id={"$in": subscription_ids_to_fetch})

        # builds the subscriptions list in the format expected by send_to_subscriptions
        subscriptions = []
        for sub in subscription_objects:
            subscriptions.append(
                {
                    "endpoint": sub.endpoint,
                    "p256dh": sub.p256dh,
                    "auth": sub.auth,
                    "_id": sub.id,
                    "_obj": sub,
                }
            )

        # delegates to the direct send method
        self.send_to_subscriptions(subscriptions, message, app=app, invalid=invalid)

    def send_to_subscriptions(
        self,
        subscriptions,
        message,
        app=None,
        vapid_private_key=None,
        vapid_email=None,
        invalid={},
    ):
        """
        Sends Web Push notifications directly to a set of subscriptions.

        This method can be used for direct messaging without requiring
        pub/sub subscriptions, while reusing the core sending logic.

        :type subscriptions: List
        :param subscriptions: List of subscription dicts with endpoint,
        p256dh, and auth keys.
        :type message: Dictionary/String
        :param message: Notification payload.
        :type app: App
        :param app: Optional App instance for VAPID config.
        :type vapid_private_key: String
        :param vapid_private_key: VAPID private key (overrides app).
        :type vapid_email: String
        :param vapid_email: VAPID contact email (overrides app).
        :type invalid: Dictionary
        :param invalid: Map of already sent endpoints to skip.
        :rtype: Dictionary
        :return: Result with success status and sent endpoints.
        """

        # verifies if the pywebpush library is available, if not
        # returns an error as we cannot send Web Push notifications
        if not pywebpush:
            return dict(success=False, error="pywebpush library not available")

        # verifies if the cryptography library is available, if not
        # returns an error as we need it for key conversion
        if not cryptography:
            return dict(success=False, error="cryptography library not available")

        # retrieves the VAPID credentials from the app configuration
        # if not provided directly through the method parameters
        if app:
            vapid_private_key = vapid_private_key or getattr(app, "vapid_key", None)
            vapid_email = vapid_email or getattr(app, "vapid_email", None)

        vapid_email = vapid_email or "mailto:noreply@pushi.io"

        # verifies if VAPID credentials are configured, if not
        # returns an error as we cannot authenticate with the push service
        if not vapid_private_key:
            return dict(success=False, error="VAPID private key not configured")

        # ensures the vapid_email has the "mailto:" prefix as required
        # by the VAPID specification
        if vapid_email and not vapid_email.startswith("mailto:"):
            vapid_email = "mailto:" + vapid_email

        # converts the VAPID private key to base64url format if it's in PEM format
        # pywebpush expects a raw base64url-encoded 32-byte private key
        if is_pem_key(vapid_private_key):
            private_key_obj = (
                cryptography.hazmat.primitives.serialization.load_pem_private_key(
                    vapid_private_key.encode("utf-8"), password=None
                )
            )
            private_bytes = private_key_obj.private_numbers().private_value.to_bytes(
                32, byteorder="big"
            )
            vapid_private_key = (
                base64.urlsafe_b64encode(private_bytes).decode("utf-8").rstrip("=")
            )

        # returns early if there are no subscriptions to notify
        if not subscriptions:
            return dict(success=True, endpoints=[])

        # prepares the notification payload, ensuring it's a JSON string
        # handles the case where message could be None or various types
        if message is None:
            payload = json.dumps({})
        elif isinstance(message, dict):
            payload = json.dumps(message)
        elif type(message) in appier.legacy.STRINGS:
            payload = message
        else:
            payload = json.dumps({"message": str(message)})

        sent_endpoints = []

        # iterates over the complete set of subscriptions that are going to
        # be notified about the message, each of them is going to receive
        # a Web Push notification
        for sub in subscriptions:
            endpoint = sub.get("endpoint")
            p256dh = sub.get("p256dh")
            auth = sub.get("auth")

            # validates that all required subscription fields are present
            if not endpoint or not p256dh or not auth:
                self.logger.warning("Invalid subscription, missing required fields")
                continue

            # in case the current subscription is present in the current
            # map of invalid items must skip iteration as the message
            # has probably already been sent to the target subscription
            sub_id = sub.get("_id", endpoint)
            if sub_id in invalid:
                continue

            # builds the subscription info dictionary required by pywebpush
            subscription_info = {
                "endpoint": endpoint,
                "keys": {
                    "p256dh": p256dh,
                    "auth": auth,
                },
            }

            # prints a debug message about the Web Push notification that
            # is going to be sent (includes endpoint)
            self.logger.debug("Sending Web Push notification to '%s'" % endpoint)

            try:
                # sends the Web Push notification using pywebpush library
                # with VAPID authentication
                pywebpush.webpush(
                    subscription_info=subscription_info,
                    data=payload,
                    vapid_private_key=vapid_private_key,
                    vapid_claims=dict(sub=vapid_email),
                )

                # adds the current subscription to the list of invalid items
                # for the current message sending stream
                invalid[sub_id] = True
                sent_endpoints.append(endpoint)

            except pywebpush.WebPushException as exception:
                # logs the error that occurred during the Web Push send
                self.logger.warning(
                    "Failed to send Web Push to '%s': %s" % (endpoint, str(exception))
                )

                # if the error is due to an expired or invalid subscription (410 Gone
                # or 404 Not Found), removes the subscription from the database
                if exception.response and exception.response.status_code in (404, 410):
                    self.logger.info("Subscription expired: '%s'" % endpoint)
                    sub_obj = sub.get("_obj")
                    if sub_obj:
                        try:
                            sub_obj.delete()
                        except Exception:
                            pass

            except Exception as exception:
                # logs any other unexpected errors
                self.logger.error(
                    "Unexpected error sending Web Push to '%s': %s"
                    % (endpoint, str(exception))
                )

        return dict(success=True, endpoints=sent_endpoints)

    def load(self):
        """
        Loads all Web Push subscriptions from the database and
        populates the in-memory subscription map.

        Called during handler initialization to preload subscriptions
        into memory for fast lookup during message sending.
        """

        subs = pushi.WebPush.find()
        for sub in subs:
            app_id = sub.app_id
            subscription_id = sub.id
            event = sub.event
            self.add(app_id, subscription_id, event)

    def add(self, app_id, subscription_id, event):
        """
        Adds a Web Push subscription to the in-memory map.

        :type app_id: String
        :param app_id: The application identifier.
        :type subscription_id: String
        :param subscription_id: The subscription object identifier from
        the database.
        :type event: String
        :param event: The event/channel name.
        """

        events = self.subs.get(app_id, {})
        subscription_ids = events.get(event, [])
        if subscription_id not in subscription_ids:
            subscription_ids.append(subscription_id)
        events[event] = subscription_ids
        self.subs[app_id] = events

    def remove(self, app_id, subscription_id, event):
        """
        Removes a Web Push subscription from the in-memory map.

        :type app_id: String
        :param app_id: The application identifier.
        :type subscription_id: String
        :param subscription_id: The subscription object identifier from
        the database.
        :type event: String
        :param event: The event/channel name.
        """
        events = self.subs.get(app_id, {})
        subscription_ids = events.get(event, [])
        if subscription_id in subscription_ids:
            subscription_ids.remove(subscription_id)

    def subscriptions(self, endpoint=None, event=None):
        """
        Retrieves Web Push subscriptions from the database with optional filtering.

        :type endpoint: String
        :param endpoint: Optional endpoint URL to filter by (default: None).
        :type event: String
        :param event: Optional event/channel name to filter by (default: None).
        :rtype: Dictionary
        :return: Dictionary containing list of mapped subscriptions under
        the 'subscriptions' key.
        """

        filter = dict()
        if endpoint:
            filter["endpoint"] = endpoint
        if event:
            filter["event"] = event
        subscriptions = pushi.WebPush.find(map=True, **filter)
        return dict(subscriptions=subscriptions)

    def subscribe(self, web_push, auth=None, unsubscribe=True):
        """
        Subscribes a Web Push endpoint to an event/channel.

        Validates private channel access and optionally removes existing
        subscriptions for the same endpoint to prevent duplicates.

        :type web_push: WebPush
        :param web_push: The WebPush model instance to be subscribed.
        :type auth: String
        :param auth: Optional authentication token for private channels
        (default: None).
        :type unsubscribe: bool
        :param unsubscribe: Whether to unsubscribe existing subscriptions
        for the same endpoint (default: True).
        :rtype: WebPush
        :return: The saved WebPush model instance.
        """

        self.logger.debug(
            "Subscribing '%s' for '%s'" % (web_push.endpoint, web_push.event)
        )

        # verifies if the event is a private channel (requires authentication)
        is_private = (
            web_push.event.startswith("private-")
            or web_push.event.startswith("presence-")
            or web_push.event.startswith("peer-")
            or web_push.event.startswith("personal-")
        )

        # if the channel is private, verifies the authentication token
        if is_private:
            self.owner.verify(web_push.app_key, web_push.endpoint, web_push.event, auth)

        # if unsubscribe is enabled, removes any existing subscriptions
        # for the same endpoint (prevents duplicates)
        if unsubscribe:
            self.unsubscribe(web_push.endpoint, force=False)

        # checks if a subscription already exists for this endpoint and event
        exists = pushi.WebPush.exists(endpoint=web_push.endpoint, event=web_push.event)
        if exists:
            web_push = exists
        else:
            web_push.save()

        self.logger.debug(
            "Subscribed '%s' for '%s'" % (web_push.endpoint, web_push.event)
        )

        return web_push

    def unsubscribe(self, endpoint, event=None, force=True):
        """
        Unsubscribes a Web Push endpoint from an event/channel.

        :type endpoint: String
        :param endpoint: The push endpoint URL to unsubscribe.
        :type event: String
        :param event: Optional event/channel name. If None, unsubscribes
        from all events (default: None).
        :type force: bool
        :param force: Whether to raise an error if subscription not found
        (default: True).
        :rtype: WebPush
        :return: The deleted WebPush model instance or None if not found.
        """

        self.logger.debug("Unsubscribing '%s' from '%s'" % (endpoint, event or "*"))

        kwargs = dict(endpoint=endpoint, raise_e=force)
        if event:
            kwargs["event"] = event

        web_push = pushi.WebPush.get(**kwargs)
        if not web_push:
            return None

        web_push.delete()

        self.logger.debug("Unsubscribed '%s' for '%s'" % (endpoint, event or "*"))

        return web_push

    def unsubscribes(self, endpoint, event=None):
        """
        Unsubscribes a Web Push endpoint from multiple events/channels.

        Finds and deletes all matching subscriptions for the given
        endpoint, optionally filtered by event name.

        :type endpoint: String
        :param endpoint: The push endpoint URL to unsubscribe.
        :type event: String
        :param event: Optional event/channel name to filter by
        (default: None).
        :rtype: List
        :return: List of deleted WebPush model instances.
        """

        kwargs = dict(endpoint=endpoint)
        if event:
            kwargs["event"] = event

        web_pushes = pushi.WebPush.find(**kwargs)
        for web_push in web_pushes:
            web_push.delete()

        return web_pushes


def is_pem_key(key):
    """
    Checks if the provided key is in PEM format.

    :type key: String
    :param key: The key string to check.
    :rtype: bool
    :return: True if the key is PEM-encoded, False otherwise.
    """

    return key and key.strip().startswith("-----BEGIN")
