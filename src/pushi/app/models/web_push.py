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

import appier

from . import base


class WebPush(base.PushiBase):
    """
    Database model for W3C Web Push API subscriptions.

    Stores the subscription information required to send push notifications
    to Web browsers, including the push service endpoint and encryption keys.
    Each record represents a single browser's subscription to a specific event.

    Cardinality:
        - One browser endpoint can subscribe to multiple events (multiple records).
        - One event can have many WebPush subscriptions (many browser endpoints).
        - This forms an N:M relationship between browser endpoints and events.

    Lifecycle:
        - Created when a browser subscribes to push notifications via the API.
        - On create/update: Registers the subscription with the WebPushHandler
          in the application state for event delivery.
        - On delete: Removes the subscription from the WebPushHandler.
        - The handler maintains an in-memory mapping for efficient event routing.

    Encryption:
        - The `p256dh` and `auth` fields contain browser-generated encryption keys.
        - Messages are encrypted using ECDH with the p256dh public key.
        - The auth secret provides an additional authentication layer.

    Cautions:
        - Endpoint expiration: Browser endpoints can become invalid over time
          (user clears data, changes permissions). Handle delivery failures gracefully.
        - State synchronization: If application state is unavailable, handler
          operations are silently skipped (guard: `self.state and ...`).
        - VAPID required: The parent App must have `vapid_key` and `vapid_email`
          configured for Web Push to function.
        - Instance scoping: Subscriptions are scoped to an app instance via PushiBase.

    Related models:
        - App: Provides VAPID credentials for authentication.
        - PushiEvent: The events that trigger push notifications.

    :see: https://w3c.github.io/push-api
    """

    endpoint = appier.field(
        index=True,
        description="Push Endpoint",
        meta="url",
        observations="""The push service endpoint URL where
        notifications will be sent (provided by the browser)""",
    )
    """
    The push service endpoint URL provided by the browser's Push API.
    This URL is unique per browser/device and is where notifications
    are sent via HTTP POST requests.

    :type: str
    """

    p256dh = appier.field(
        description="P256DH Key",
        meta="longtext",
        observations="""The client's public key for encryption
        (base64url-encoded, used for message encryption)""",
    )
    """
    The client's P-256 ECDH public key in base64url encoding.
    Used for encrypting push message payloads so only the
    intended browser can decrypt them.

    :type: str
    """

    auth = appier.field(
        description="Auth Secret",
        meta="longtext",
        observations="""The authentication secret for encryption
        (base64url-encoded, used for message authentication)""",
    )
    """
    The authentication secret in base64url encoding.
    Provides an additional layer of message authentication
    to prevent tampering with encrypted payloads.

    :type: str
    """

    event = appier.field(
        index=True,
        description="Event",
        observations="""The channel/event name this subscription
        is registered for (can include private-, presence-, etc.)""",
    )
    """
    The event channel name this subscription is registered for.
    Can include channel prefixes like `private-` or `presence-`
    for access control purposes.

    :type: str
    """

    @classmethod
    def validate(cls):
        return super(WebPush, cls).validate() + [
            appier.not_null("endpoint"),
            appier.not_empty("endpoint"),
            appier.not_null("p256dh"),
            appier.not_empty("p256dh"),
            appier.not_null("auth"),
            appier.not_empty("auth"),
            appier.not_null("event"),
            appier.not_empty("event"),
        ]

    @classmethod
    def list_names(cls):
        return ["id", "endpoint", "event"]

    def pre_update(self):
        base.PushiBase.pre_update(self)
        previous = self.__class__.get(id=self.id)
        if self.state:
            self.state.web_push_handler.remove(
                previous.app_id, previous.id, previous.event
            )

    def post_create(self):
        base.PushiBase.post_create(self)
        if self.state:
            self.state.web_push_handler.add(self.app_id, self.id, self.event)

    def post_update(self):
        base.PushiBase.post_update(self)
        if self.state:
            self.state.web_push_handler.add(self.app_id, self.id, self.event)

    def post_delete(self):
        base.PushiBase.post_delete(self)
        if self.state:
            self.state.web_push_handler.remove(self.app_id, self.id, self.event)
