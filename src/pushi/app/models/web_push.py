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

    Stores the subscription information required to send
    push notifications to web browsers, including the
    push service endpoint and encryption keys.
    """

    endpoint = appier.field(
        index=True,
        description="Push Endpoint",
        meta="url",
        observations="""The push service endpoint URL where
        notifications will be sent (provided by the browser)""",
    )

    p256dh = appier.field(
        description="P256DH Key",
        meta="longtext",
        observations="""The client's public key for encryption
        (base64url-encoded, used for message encryption)""",
    )

    auth = appier.field(
        description="Auth Secret",
        meta="longtext",
        observations="""The authentication secret for encryption
        (base64url-encoded, used for message authentication)""",
    )

    event = appier.field(
        index=True,
        description="Event",
        observations="""The channel/event name this subscription
        is registered for (can include private-, presence-, etc.)""",
    )

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
        return ["endpoint", "event"]

    def pre_update(self):
        base.PushiBase.pre_update(self)
        previous = self.__class__.get(id=self.id)
        self.state and self.state.web_push_handler.remove(
            previous.app_id, previous.id, previous.event
        )

    def post_create(self):
        base.PushiBase.post_create(self)
        self.state and self.state.web_push_handler.add(self.app_id, self.id, self.event)

    def post_update(self):
        base.PushiBase.post_update(self)
        self.state and self.state.web_push_handler.add(self.app_id, self.id, self.event)

    def post_delete(self):
        base.PushiBase.post_delete(self)
        self.state and self.state.web_push_handler.remove(
            self.app_id, self.id, self.event
        )
