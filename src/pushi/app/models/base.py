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
import appier_extras


class PushiBase(appier_extras.admin.Base):
    """
    Abstract base model providing multi-tenancy and application scoping.

    This is the foundation class for all Pushi domain models. It extends the
    Appier admin base model with instance-based isolation, ensuring that each
    application (App) has its own isolated namespace for all related entities.

    Multi-tenancy mechanism:
        - The `instance` field stores the owning App's `ident` value.
        - Query methods (get, find, count) automatically filter by the current
          session's `app_id` when available.
        - On creation, the `instance` is set from the current `app_id`.

    Query behavior:
        - All queries automatically scope to the current app context.
        - The `app_id` is retrieved from the request session.
        - If no `app_id` is in session, queries return cross-tenant results
          (admin access pattern).

    Properties:
        - `state`: Returns the global Pushi application state object.
        - `app_id`: Returns the owning application's identifier.
        - `app_key`: Returns the owning application's API key (via state lookup).

    Lifecycle:
        - On pre_create: Sets `instance` from the current `app_id` if available.
        - The `instance` field is immutable after creation.

    Cautions:
        - Session dependency: Multi-tenancy relies on `app_id` being present in
          the request session. Ensure proper authentication sets this value.
        - Admin access: Without `app_id` in session, queries are not scoped,
          which may expose data across tenants if not handled carefully.
        - State availability: The `state` property may return None if the
          application state is not initialized.
        - Inheritance order: Child classes calling super() in hooks must ensure
          proper call chain to maintain multi-tenancy behavior.

    Related models:
        - App: The application model whose `ident` is stored in `instance`.
        - All domain models: Subscription, Association, PushiEvent, APN, Web, WebPush.
    """

    instance = appier.field(
        index=True,
        safe=True,
        immutable=True,
        observations="""App instance identifier for multi-tenant scoping""",
    )
    """
    The application instance identifier that scopes this record.
    Set automatically to the owning App's `ident` on creation.
    Used for multi-tenant isolation in all query operations.

    :type: str
    """

    @classmethod
    def get(cls, *args, **kwargs):
        request = appier.get_request()
        app_id = request.session.get("app_id", None)
        if app_id:
            kwargs["instance"] = app_id
        return super(PushiBase, cls).get(cls, *args, **kwargs)

    @classmethod
    def find(cls, *args, **kwargs):
        request = appier.get_request()
        app_id = request.session.get("app_id", None)
        if app_id:
            kwargs["instance"] = app_id
        return super(PushiBase, cls).find(cls, *args, **kwargs)

    @classmethod
    def count(cls, *args, **kwargs):
        request = appier.get_request()
        app_id = request.session.get("app_id", None)
        if app_id:
            kwargs["instance"] = app_id
        return super(PushiBase, cls).count(cls, *args, **kwargs)

    @classmethod
    def exists(cls, *args, **kwargs):
        previous = cls.find(*args, **kwargs)
        return previous[0] if previous else None

    def pre_create(self):
        appier_extras.admin.Base.pre_create(self)
        if self.app_id:
            self.instance = self.app_id

    @property
    def state(self):
        app = appier.get_app()
        return app.state

    @property
    def app_id(self):
        if hasattr(self, "instance"):
            return self.instance
        request = appier.get_request()
        return request.session.get("app_id", None)

    @property
    def app_key(self):
        if not self.app_id:
            return None
        return self.state.app_id_to_app_key(self.app_id)
