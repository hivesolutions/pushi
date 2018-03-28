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

class APNController(appier.Controller):

    @appier.private
    @appier.route("/apns", "GET")
    def list(self):
        token = self.field("token", None)
        event = self.field("event", None)
        return self.state.apn_handler.subscriptions(token = token, event = event)

    @appier.private
    @appier.route("/apns", "POST")
    def create(self):
        auth = self.field("auth", None)
        unsubscribe = self.field("unsubscribe", False, cast = bool)
        apn = pushi.APN.new()
        apn = self.state.apn_handler.subscribe(
            apn,
            auth = auth,
            unsubscribe = unsubscribe
        )
        return apn.map()

    @appier.private
    @appier.route("/apns/<token>", "DELETE")
    def deletes(self, token):
        apns = self.state.apn_handler.unsubscribes(token)
        return dict(
            subscriptions = [apn.map() for apn in apns]
        )

    @appier.private
    @appier.route("/apns/<token>/<regex('[\.\w-]+'):event>", "DELETE")
    def delete(self, token, event):
        force = self.field("force", False, cast = bool)
        apn = self.state.apn_handler.unsubscribe(token, event = event, force = force)
        return apn.map()
