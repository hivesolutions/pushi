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

        # verifies if the pywebpush library is available, if not
        # logs a warning and returns immediately
        if not pywebpush:
            self.logger.warning(
                "pywebpush library not available, skipping Web Push notifications"
            )
            return

        # verifies if the cryptography library is available, if not
        # logs a warning and returns immediately
        if not cryptography:
            self.logger.warning(
                "cryptography library not available, skipping Web Push notifications"
            )
            return

        # retrieves the reference to the app structure associated with the
        # id for which the message is being sent
        app = self.owner.get_app(app_id=app_id)

        # retrieves the VAPID credentials from the app configuration
        vapid_private_key = app.vapid_key if hasattr(app, "vapid_key") else None
        vapid_email = (
            app.vapid_email
            if hasattr(app, "vapid_email") and app.vapid_email
            else "mailto:noreply@pushi.io"
        )

        # ensures the `vapid_email` has the "mailto:" prefix
        if vapid_email and not vapid_email.startswith("mailto:"):
            vapid_email = "mailto:" + vapid_email

        # verifies if VAPID credentials are configured, if not
        # logs a warning and returns immediately
        if not vapid_private_key:
            self.logger.warning(
                "VAPID credentials not configured for app '%s', skipping Web Push"
                % app_id
            )
            return

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

        # retrieves the app key for the retrieved app by unpacking the current
        # app structure into the appropriate values
        app_key = app.key

        # saves the original event name for the received event, so that it may
        # be used later for debugging/log purposes
        root_event = event

        # tries to extract the message from the JSON data structure, trying
        # multiple keys in sequence (data, push, web_push, message)
        message = json_d.get("data", None)
        message = json_d.get("push", message)
        message = json_d.get("web_push", message)
        message = json_d.get("message", message)

        # resolves the complete set of (extra) channels for the provided
        # event assuming that it may be associated with alias, then creates
        # the complete list of events containing also the "extra" events
        extra = self.owner.get_channels(app_key, event)
        events = [event] + extra

        # retrieves the complete set of subscriptions for the current Web Push
        # infrastructure to be able to resolve the appropriate subscription objects
        subs = self.subs.get(app_id, {})

        # creates the initial list of subscription objects to be notified and then
        # populates the list with the various subscriptions associated with the
        # complete set of resolved events, note that a set is created at the end
        # so that one subscription gets notified only once (no double notifications)
        subscriptions = []
        for event in events:
            _subscriptions = subs.get(event, [])
            subscriptions.extend(_subscriptions)
        subscriptions = list(set(subscriptions))
        count = len(subscriptions)

        # prints a logging message about the various (Web Push) subscriptions
        # that were found for the event that was triggered
        self.logger.debug(
            "Found %d Web Push subscription(s) for '%s'" % (count, root_event)
        )

        # prepares the notification payload, ensuring it's a JSON string
        # handles the case where message could be None or various types
        if message == None:
            payload = json.dumps({})
        elif isinstance(message, dict):
            payload = json.dumps(message)
        elif type(message) in appier.legacy.STRINGS:
            payload = message
        else:
            payload = json.dumps({"message": str(message)})

        # batch fetch all subscription objects from the database to avoid N+1 queries
        # filters out subscriptions that are already in the invalid map
        subscription_ids_to_fetch = [sid for sid in subscriptions if sid not in invalid]
        subscription_objects = pushi.WebPush.find(id={"$in": subscription_ids_to_fetch})
        subscription_map = {sub.id: sub for sub in subscription_objects}

        # iterates over the complete set of subscriptions that are going to
        # be notified about the message, each of them is going to receive
        # a Web Push notification
        for subscription_id in subscriptions:
            # in case the current subscription ID is present in the current
            # map of invalid items must skip iteration as the message
            # has probably already been sent to the target subscription
            if subscription_id in invalid:
                continue

            # retrieves the subscription object from the pre-fetched map
            subscription_obj = subscription_map.get(subscription_id)
            if not subscription_obj:
                self.logger.warning(
                    "Web push subscription '%s' not found in database" % subscription_id
                )
                continue

            # builds the subscription info dictionary required by pywebpush
            subscription_info = {
                "endpoint": subscription_obj.endpoint,
                "keys": {
                    "p256dh": subscription_obj.p256dh,
                    "auth": subscription_obj.auth,
                },
            }

            # prints a debug message about the Web Push notification that
            # is going to be sent (includes endpoint)
            self.logger.debug(
                "Sending Web Push notification to '%s'" % subscription_obj.endpoint
            )

            try:
                # sends the Web Push notification using pywebpush library
                # with VAPID authentication
                pywebpush.webpush(
                    subscription_info=subscription_info,
                    data=payload,
                    vapid_private_key=vapid_private_key,
                    vapid_claims=dict(sub=vapid_email),
                )

                # adds the current subscription ID to the list of invalid items
                # for the current message sending stream
                invalid[subscription_id] = True

            except pywebpush.WebPushException as exception:
                # logs the error that occurred during the Web Push send
                self.logger.warning(
                    "Failed to send Web Push to '%s': %s"
                    % (subscription_obj.endpoint, str(exception))
                )

                # if the error is due to an expired or invalid subscription (410 Gone
                # or 404 Not Found), removes the subscription from the database
                if exception.response and exception.response.status_code in (404, 410):
                    self.logger.info(
                        "Removing expired Web Push subscription '%s'" % subscription_id
                    )
                    try:
                        subscription_obj.delete()
                    except Exception as delete_exception:
                        self.logger.error(
                            "Failed to delete expired subscription: %s"
                            % str(delete_exception)
                        )

            except Exception as exception:
                # logs any other unexpected errors
                self.logger.error(
                    "Unexpected error sending Web Push to '%s': %s"
                    % (subscription_obj.endpoint, str(exception))
                )

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
