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


class PushiEvent(base.PushiBase):
    """
    Immutable record of an event published through the Pushi system.

    This model persists the complete event payload including metadata and
    user-provided data. Events are write-once and cannot be modified after
    creation, ensuring an auditable history of all published messages.

    Cardinality:
        - One PushiEvent can have many Associations (one per recipient user).
        - Events are identified globally by their `mid` (Message ID).
        - Multiple events can belong to the same channel.

    Lifecycle:
        - Created automatically when `state.log_channel()` or `state.send_event()`
          is called with persistence enabled.
        - The `mid` and `timestamp` are system-generated and cannot be overridden
          in the event data payload.
        - Events are immutable post-creation (all fields marked immutable).

    Data integrity:
        - The `pre_save` hook verifies that the `data` dict does not contain
          `mid` or `timestamp` keys to prevent payload conflicts.
        - System fields are kept separate from user-provided data.

    Cautions:
        - Storage growth: Events accumulate indefinitely; consider implementing
          retention policies for high-volume deployments.
        - Large payloads: The `data` field stores arbitrary dicts; no size limit
          is enforced at the model level.
        - Instance scoping: Events are scoped to an app instance via PushiBase.

    Related models:
        - Association: Links events to users for personal event retrieval.
        - Subscription: Determines which users receive events on a channel.
    """

    mid = appier.field(
        index=True,
        immutable=True,
        default=True,
        description="MID",
        observations="""Unique Message ID (UUID), auto-generated on creation""",
    )
    """
    The Message ID, a unique UUID identifying this event globally.
    Auto-generated on event creation and used as the primary lookup key
    for event retrieval and association linking.

    :type: str
    """

    channel = appier.field(
        index=True,
        immutable=True,
        observations="""Channel name this event was published to""",
    )
    """
    The name of the channel this event was published to. Used for
    filtering and routing events to subscribed clients.

    :type: str
    """

    owner_id = appier.field(
        immutable=True,
        description="Owner ID",
        observations="""Optional identifier of the entity that triggered this event""",
    )
    """
    Optional identifier of the entity that triggered this event.
    Can represent a user, service, or system component for auditing purposes.

    :type: str
    """

    timestamp = appier.field(
        type=float,
        index=True,
        immutable=True,
        meta="datetime",
        observations="""Unix timestamp (with fractional seconds) of event creation""",
    )
    """
    Unix timestamp (with fractional seconds) when the event was created.
    System-generated and cannot be provided in the event data.

    :type: float
    """

    data = appier.field(
        type=dict,
        immutable=True,
        meta="longtext",
        observations="""Event payload dict; must not contain reserved keys (mid, timestamp)""",
    )
    """
    The event payload containing arbitrary user-provided data.
    Must not contain `mid` or `timestamp` keys as these are reserved
    for system use and validated on save.

    :type: dict
    """

    @classmethod
    def validate(cls):
        return super(PushiEvent, cls).validate() + [
            appier.not_null("mid"),
            appier.not_empty("mid"),
            appier.not_null("channel"),
            appier.not_empty("channel"),
            appier.not_null("timestamp"),
        ]

    @classmethod
    def list_names(cls):
        return ["mid", "channel", "owner_id", "timestamp"]

    def pre_save(self):
        base.PushiBase.pre_save(self)
        appier.verify(not "mid" in self.data)
        appier.verify(not "timestamp" in self.data)

    @classmethod
    @appier.operation(
        name="Trigger",
        description="""Triggers a new event on the pushi system running
        the complete set of handlers associated""",
        parameters=(
            ("App ID", "app_id", str),
            ("Event", "event", str),
            ("Data", "data", "longtext"),
            ("Persist", "persist", bool, True),
        ),
    )
    def trigger_s(cls, app_id, event, data, persist=True):
        state = appier.get_app().state
        state.trigger(app_id, event, data, persist=persist)
