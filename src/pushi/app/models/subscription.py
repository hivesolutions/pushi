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


class Subscription(base.PushiBase):
    """
    Model that links users to event channels they wish to receive messages on.

    This model creates a subscription relationship where a user (identified by
    `user_id`) subscribes to a specific event channel. When events are published
    to that channel, the user becomes eligible to receive them.

    Cardinality:
        - One User (user_id) can have many Subscriptions (one per channel).
        - One Event channel can have many Subscriptions (many users).
        - This forms an N:M relationship between users and event channels.

    Lifecycle:
        - On create/update: Registers an alias in the application state mapping
          the user's personal channel (`personal-{user_id}`) to the event channel.
        - On delete: Removes the alias from the application state.
        - The alias mechanism enables routing events to all subscribed users.

    State synchronization:
        - The model hooks (post_create, post_update, post_delete) keep the
          in-memory state in sync with persisted subscriptions.
        - On pre_update, the previous alias is removed before adding the new one.

    Cautions:
        - Alias management: If the application state is not available, alias
          operations are silently skipped (guard: `self.state and ...`).
        - No uniqueness constraint: Multiple subscriptions with the same user_id
          and event combination can exist; consider enforcing uniqueness at the
          application level if required.
        - Instance scoping: Subscriptions are scoped to an app instance via PushiBase.

    Related models:
        - Association: Created when events are triggered to track delivery.
        - PushiEvent: The actual event data published to channels.
    """

    user_id = appier.field(
        index=True,
        description="User ID",
        observations="""External identifier of the subscribing user""",
    )
    """
    The unique identifier of the subscribing user. This is an external
    identifier provided by the client application, not a foreign key
    to a local user model.

    :type: str
    """

    event = appier.field(
        index=True,
        observations="""Event channel name (supports private-/presence- prefixes)""",
    )
    """
    The name of the event channel the user is subscribing to. Can include
    channel prefixes like `private-` or `presence-` for access control.

    :type: str
    """

    @classmethod
    def validate(cls):
        return super(Subscription, cls).validate() + [
            appier.not_null("user_id"),
            appier.not_empty("user_id"),
            appier.not_null("event"),
            appier.not_empty("event"),
        ]

    @classmethod
    def list_names(cls):
        return ["user_id", "event"]

    def pre_update(self):
        base.PushiBase.pre_update(self)
        previous = self.__class__.get(id=self.id)
        if self.state:
            self.state.remove_alias(
                previous.app_key, "personal-" + previous.user_id, previous.event
            )

    def post_create(self):
        base.PushiBase.post_create(self)
        if self.state:
            self.state.add_alias(self.app_key, "personal-" + self.user_id, self.event)

    def post_update(self):
        base.PushiBase.post_update(self)
        if self.state:
            self.state.add_alias(self.app_key, "personal-" + self.user_id, self.event)

    def post_delete(self):
        base.PushiBase.post_delete(self)
        if self.state:
            self.state.remove_alias(
                self.app_key, "personal-" + self.user_id, self.event
            )
