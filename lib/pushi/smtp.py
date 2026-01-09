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


class SMTPAPI(object):
    def list_smtps(self, email=None, event=None):
        # runs the list operation for the SMTP subscriptions
        # with optional filtering by email and/or event
        params = dict()
        if email:
            params["email"] = email
        if event:
            params["event"] = event
        result = self.get(self.base_url + "smtps", params=params)
        return result

    def create_smtp(self, email, event, auth=None, unsubscribe=True):
        # runs the SMTP subscription operation for the provided
        # email and event, this operation uses the currently
        # defined app id for the operation, then returns the
        # resulting dictionary to the caller method
        result = self.post(
            self.base_url + "smtps",
            params=dict(auth=auth, unsubscribe=unsubscribe),
            data_j=dict(email=email, event=event),
        )
        return result

    def delete_smtp(self, email, event, force=False):
        # runs the unsubscription operation for the provided
        # email and event, this operation uses the currently
        # defined app id for the operation, then returns the
        # resulting dictionary to the caller method
        params = dict()
        if force:
            params["force"] = force
        result = self.delete(
            self.base_url + "smtps/%s/%s" % (email, event), params=params
        )
        return result

    def delete_smtps(self, email):
        # runs the unsubscription operation for all subscriptions
        # associated with the provided email, then returns the
        # resulting dictionary to the caller method
        result = self.delete(self.base_url + "smtps/%s" % email)
        return result

    def subscribe_smtp(self, *args, **kwargs):
        return self.create_smtp(*args, **kwargs)

    def unsubscribe_smtp(self, *args, **kwargs):
        return self.delete_smtp(*args, **kwargs)
