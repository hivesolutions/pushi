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


class WebPushAPI(object):
    def list_web_pushes(self, endpoint=None, event=None):
        # runs the list operation for the Web Push subscriptions
        # with optional filtering by endpoint and/or event
        params = dict()
        if endpoint:
            params["endpoint"] = endpoint
        if event:
            params["event"] = event
        result = self.get(self.base_url + "web_pushes", params=params)
        return result

    def create_web_push(
        self, endpoint, p256dh, auth, event, auth_token=None, unsubscribe=True
    ):
        # runs the Web Push subscription operation for the provided
        # endpoint and event, this operation uses the currently
        # defined app id for the operation, then returns the
        # resulting dictionary to the caller method
        result = self.post(
            self.base_url + "web_pushes",
            params=dict(auth=auth_token, unsubscribe=unsubscribe),
            data_j=dict(endpoint=endpoint, p256dh=p256dh, auth=auth, event=event),
        )
        return result

    def delete_web_push(self, endpoint, event=None, force=False):
        # runs the unsubscription operation for the provided
        # endpoint, optionally filtered by event; this operation
        # uses the currently defined app id for the operation,
        # then returns the resulting dictionary to the caller method
        endpoint_encoded = appier.legacy.quote(endpoint, safe="")
        params = dict()
        if event:
            params["event"] = event
        if force:
            params["force"] = force
        result = self.delete(
            self.base_url + "web_pushes/%s" % endpoint_encoded, params=params
        )
        return result

    def delete_web_pushes(self, endpoint):
        # runs the unsubscription operation for all subscriptions
        # associated with the provided endpoint, this is an alias
        # for delete_web_push without an event filter
        return self.delete_web_push(endpoint)

    def get_vapid_public_key(self):
        # retrieves the VAPID public key for the current app,
        # this key is needed by browsers to subscribe to push
        # notifications using the Web Push API
        result = self.get(self.base_url + "apps/vapid_key")
        return result

    def subscribe_web_push(self, *args, **kwargs):
        return self.create_web_push(*args, **kwargs)

    def unsubscribe_web_push(self, *args, **kwargs):
        return self.delete_web_push(*args, **kwargs)
