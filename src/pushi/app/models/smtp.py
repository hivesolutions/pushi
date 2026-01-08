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


class SMTP(base.PushiBase):
    """
    Email subscription model for SMTP-based push notifications.

    This model enables email notifications by registering email addresses
    that will receive messages when events are published to specific channels.

    Cardinality:
        - One email can subscribe to multiple events (multiple records).
        - One event can have many email subscriptions (many emails).
        - This forms an N:M relationship between emails and event channels.

    Lifecycle:
        - Created when an email address is registered for notifications.
        - On create/update: Registers the email with the SMTPHandler in the
          application state for event delivery.
        - On delete: Removes the email from the SMTPHandler.
        - The handler maintains an in-memory mapping for efficient event routing.

    Delivery behavior:
        - When an event is published to a subscribed channel, an email
          is sent to the registered address with the event payload.
        - Delivery uses the netius SMTP client configured via environment
          variables (SMTP_HOST, SMTP_PORT, etc.).

    Cautions:
        - Email validation: No email format validation at model level; invalid
          emails will cause delivery failures at runtime.
        - SMTP configuration: Requires proper SMTP settings to function.
        - State synchronization: If application state is unavailable, handler
          operations are silently skipped (guard: `self.state and ...`).
        - No uniqueness constraint: Duplicate email/event combinations can exist.
        - Instance scoping: Subscriptions are scoped to an app instance via PushiBase.

    Related models:
        - PushiEvent: The events that trigger email notifications.
        - App: The parent application that owns this subscription.

    :see: https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol
    """

    email = appier.field(
        index=True,
        description="Email",
        meta="email",
        observations="""Email address that receives notifications on event publish""",
    )
    """
    The email address that will receive notifications when events
    are published to the subscribed channel.

    :type: str
    """

    event = appier.field(
        index=True,
        observations="""Event channel name this email subscribes to""",
    )
    """
    The name of the event channel this email is subscribed to.
    Can include channel prefixes like `private-` or `presence-`.

    :type: str
    """

    @classmethod
    def validate(cls):
        return super(SMTP, cls).validate() + [
            appier.not_null("email"),
            appier.not_empty("email"),
            appier.not_null("event"),
            appier.not_empty("event"),
        ]

    @classmethod
    def list_names(cls):
        return ["id", "email", "event"]

    @classmethod
    def _underscore(cls, plural=True):
        return "smtps" if plural else "smtp"

    @classmethod
    def _readable(cls, plural=False):
        return "SMTPs" if plural else "SMTP"

    def pre_update(self):
        base.PushiBase.pre_update(self)
        previous = self.__class__.get(id=self.id)
        if self.state:
            self.state.smtp_handler.remove(
                previous.app_id, previous.email, previous.event
            )

    def post_create(self):
        base.PushiBase.post_create(self)
        if self.state:
            self.state.smtp_handler.add(self.app_id, self.email, self.event)

    def post_update(self):
        base.PushiBase.post_update(self)
        if self.state:
            self.state.smtp_handler.add(self.app_id, self.email, self.event)

    def post_delete(self):
        base.PushiBase.post_delete(self)
        if self.state:
            self.state.smtp_handler.remove(self.app_id, self.email, self.event)
