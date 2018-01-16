#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (c) 2008-2018 Hive Solutions Lda.
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

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

class SubscriptionAPI(object):

    def create_subscription(self, user_id, event):
        # runs the subscription operation for the provided
        # user id and event, this operation uses the currently
        # defined app id for the operation, then returns the
        # resulting dictionary to the caller method
        result = self.post(
            self.base_url + "subscriptions",
            data_j = dict(
                user_id = user_id,
                event = event
            )
        )
        return result

    def delete_subscription(self, user_id, event):
        # runs the unsubscription operation for the provided
        # user id and event, this operation uses the currently
        # defined app id for the operation, then returns the
        # resulting dictionary to the caller method
        result = self.delete(
            self.base_url + "subscriptions/%s/%s" % (user_id, event)
        )
        return result

    def subscribe(self, *args, **kwargs):
        return self.create_subscription(*args, **kwargs)

    def unsubscribe(self, *args, **kwargs):
        return self.delete_subscription(*args, **kwargs)
