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

import appier

import pushi

class SubscriptionController(appier.Controller):

    @appier.private
    @appier.route("/subscriptions", "GET")
    def list(self):
        user_id = self.field("user_id", None)
        event = self.field("event", None)
        filter = dict()
        if user_id: filter["user_id"] = user_id
        if event: filter["event"] = event
        subscriptions = pushi.Subscription.find(map = True, **filter)
        return dict(
            subscriptions = subscriptions
        )

    @appier.private
    @appier.route("/subscriptions", "POST")
    def create(self):
        subscription = pushi.Subscription.new()
        exists = pushi.Subscription.exists(
            user_id = subscription.user_id,
            event = subscription.event
        )
        if exists: subscription = exists
        else: subscription.save()
        return subscription.map()

    @appier.private
    @appier.route("/subscriptions/<user_id>/<regex('[\.\w-]+'):event>", "DELETE")
    def delete(self, user_id, event):
        force = self.field("force", False, cast = bool)
        subscription = pushi.Subscription.get(
            user_id = user_id,
            event = event,
            raise_e = force
        )
        if not subscription: return None
        subscription.delete()
        return subscription.map()
