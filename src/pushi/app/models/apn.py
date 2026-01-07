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


class APN(base.PushiBase):
    """
    Apple Push Notification (APN) subscription model for iOS devices.

    This model stores device tokens registered for push notifications via
    Apple's APNs service. Each record represents a single iOS device's
    subscription to a specific event channel.

    Cardinality:
        - One device token can subscribe to multiple events (multiple records).
        - One event can have many APN subscriptions (many devices).
        - This forms an N:M relationship between device tokens and events.

    Lifecycle:
        - Created when an iOS device registers for push notifications.
        - On create/update: Registers the token with the APNHandler in the
          application state for event delivery.
        - On delete: Removes the token from the APNHandler.
        - The handler maintains an in-memory mapping for efficient event routing.

    Token management:
        - Device tokens are provided by iOS and may change over time
          (app reinstall, device restore, etc.).
        - Invalid or expired tokens will cause delivery failures; Apple's
          feedback service should be used to clean up stale tokens.

    Cautions:
        - Token invalidation: iOS device tokens can become invalid; implement
          feedback handling to remove stale subscriptions.
        - Certificate requirements: The parent App must have valid `apn_key`
          and `apn_cer` configured, matching the `apn_sandbox` environment.
        - Sandbox vs Production: Ensure `apn_sandbox` flag matches the token's
          environment; sandbox tokens won't work in production and vice versa.
        - State synchronization: If application state is unavailable, handler
          operations are silently skipped (guard: `self.state and ...`).
        - No uniqueness constraint: Duplicate token/event combinations can exist.
        - Instance scoping: APN subscriptions are scoped to an app instance via PushiBase.

    Related models:
        - App: Provides APN credentials and sandbox configuration.
        - PushiEvent: The events that trigger push notifications.
    """

    token = appier.field(
        index=True,
        observations="""iOS device token from Apple Push Notification service""",
    )
    """
    The iOS device token provided by Apple's Push Notification service.
    This is a unique identifier for a specific app installation on a
    specific device, used to route push notifications.

    :type: str
    """

    event = appier.field(
        index=True,
        observations="""Event channel name this device subscribes to""",
    )
    """
    The name of the event channel this device is subscribed to.
    Can include channel prefixes like `private-` or `presence-`.

    :type: str
    """

    @classmethod
    def validate(cls):
        return super(APN, cls).validate() + [
            appier.not_null("token"),
            appier.not_empty("token"),
            appier.not_null("event"),
            appier.not_empty("event"),
        ]

    @classmethod
    def list_names(cls):
        return ["token", "event"]

    @classmethod
    def _underscore(cls, plural=True):
        return "apns" if plural else "apn"

    @classmethod
    def _readable(cls, plural=False):
        return "APNs" if plural else "APN"

    def pre_update(self):
        base.PushiBase.pre_update(self)
        previous = self.__class__.get(id=self.id)
        if self.state:
            self.state.apn_handler.remove(
                previous.app_id, previous.token, previous.event
            )

    def post_create(self):
        base.PushiBase.post_create(self)
        if self.state:
            self.state.apn_handler.add(self.app_id, self.token, self.event)

    def post_update(self):
        base.PushiBase.post_update(self)
        if self.state:
            self.state.apn_handler.add(self.app_id, self.token, self.event)

    def post_delete(self):
        base.PushiBase.post_delete(self)
        if self.state:
            self.state.apn_handler.remove(self.app_id, self.token, self.event)
