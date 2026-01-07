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


class Association(base.PushiBase):
    """
    Join model that links users to events they have been targeted to receive.

    This model creates a many-to-many relationship between users and events,
    enabling the retrieval of personal events for a specific user. Each
    association record represents a single user's entitlement to receive
    a specific event.

    Cardinality:
        - One User (user_id) can have many Associations (one per event received).
        - One Event (mid) can have many Associations (one per recipient user).
        - This forms an N:M relationship between users and the PushiEvent model.

    Lifecycle:
        - Created automatically when an event is triggered to a channel that has
          subscribed users (via Subscription model).
        - Used by `get_events_personal()` to retrieve all events for a given user
          by collecting association mids and fetching corresponding PushiEvent records.

    Cautions:
        - Volume growth: Each triggered event creates N associations where N equals
          the number of subscribed users on the target channel. High-traffic systems
          may accumulate associations rapidly.
        - No automatic cleanup: Old associations are not automatically purged; consider
          implementing a retention policy or periodic cleanup for long-running systems.
        - Duplicate prevention: The event sending logic uses an `invalid` dict to prevent
          duplicate associations within a single send operation, but does not check for
          existing associations in the database.
        - Instance scoping: Associations are scoped to an app instance (via PushiBase),
          ensuring multi-tenant isolation.

    Related models:
        - PushiEvent: The event model referenced by the `mid` field.
        - Subscription: Determines which users receive events on a channel.
    """

    user_id = appier.field(
        index=True,
        description="User ID",
        observations="""External identifier of the user entitled to receive the event""",
    )
    """
    The unique identifier of the user who is entitled to receive the
    associated event. This is an external identifier, not a foreign key
    to a local user model.

    :type: str
    """

    mid = appier.field(
        index=True,
        description="MID",
        observations="""Message ID (UUID) referencing the PushiEvent""",
    )
    """
    The Message ID (UUID) of the event. This references the `mid` field
    in the PushiEvent model and serves as the logical foreign key linking
    this association to its corresponding event.

    :type: str
    """

    @classmethod
    def validate(cls):
        return super(Association, cls).validate() + [
            appier.not_null("user_id"),
            appier.not_empty("user_id"),
            appier.not_null("mid"),
            appier.not_empty("mid"),
        ]

    @classmethod
    def list_names(cls):
        return ["user_id", "mid", "created"]
