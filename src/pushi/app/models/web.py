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


class Web(base.PushiBase):
    """
    Webhook registration model for HTTP callback notifications.

    This model enables server-to-server push notifications by registering
    external URLs (webhooks) that will receive HTTP POST requests when
    events are published to specific channels.

    Cardinality:
        - One URL can subscribe to multiple events (multiple records).
        - One event can have many webhook subscriptions (many URLs).
        - This forms an N:M relationship between URLs and event channels.

    Lifecycle:
        - Created when an external service registers a webhook endpoint.
        - On create/update: Registers the webhook with the WebHandler in the
          application state for event delivery.
        - On delete: Removes the webhook from the WebHandler.
        - The handler maintains an in-memory mapping for efficient event routing.

    Delivery behavior:
        - When an event is published to a subscribed channel, an HTTP POST
          request is sent to the registered URL with the event payload.
        - Delivery is typically asynchronous and may include retry logic
          (implementation dependent on WebHandler).

    Cautions:
        - URL validation: No URL format validation at model level; invalid URLs
          will cause delivery failures at runtime.
        - Endpoint availability: External endpoints may become unavailable;
          implement proper error handling and retry policies.
        - Security: Consider implementing webhook signatures or authentication
          to verify payload authenticity at the receiving end.
        - State synchronization: If application state is unavailable, handler
          operations are silently skipped (guard: `self.state and ...`).
        - No uniqueness constraint: Duplicate URL/event combinations can exist.
        - Instance scoping: Webhooks are scoped to an app instance via PushiBase.

    Related models:
        - PushiEvent: The events that trigger webhook calls.
        - App: The parent application that owns this webhook registration.

    :see: https://en.wikipedia.org/wiki/Webhook
    """

    url = appier.field(
        index=True,
        description="URL",
        meta="url",
        observations="""Webhook endpoint URL that receives HTTP POST on event publish""",
    )
    """
    The webhook endpoint URL that will receive HTTP POST requests
    when events are published to the subscribed channel.

    :type: str
    """

    event = appier.field(
        index=True,
        observations="""Event channel name this webhook subscribes to""",
    )
    """
    The name of the event channel this webhook is subscribed to.
    Can include channel prefixes like `private-` or `presence-`.

    :type: str
    """

    @classmethod
    def validate(cls):
        return super(Web, cls).validate() + [
            appier.not_null("url"),
            appier.not_empty("url"),
            appier.not_null("event"),
            appier.not_empty("event"),
        ]

    @classmethod
    def list_names(cls):
        return ["id", "url", "event"]

    def pre_update(self):
        base.PushiBase.pre_update(self)
        previous = self.__class__.get(id=self.id)
        if self.state:
            self.state.web_handler.remove(previous.app_id, previous.url, previous.event)

    def post_create(self):
        base.PushiBase.post_create(self)
        if self.state:
            self.state.web_handler.add(self.app_id, self.url, self.event)

    def post_update(self):
        base.PushiBase.post_update(self)
        if self.state:
            self.state.web_handler.add(self.app_id, self.url, self.event)

    def post_delete(self):
        base.PushiBase.post_delete(self)
        if self.state:
            self.state.web_handler.remove(self.app_id, self.url, self.event)
