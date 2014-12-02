#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (C) 2008-2014 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2014 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import appier

import pushi

class AppController(appier.Controller):

    @appier.private
    @appier.route("/apps", "GET")
    def list(self):
        apps = pushi.App.find(map = True)
        return dict(
            apps = apps
        )

    @appier.route("/apps", "POST")
    def create(self):
        app = pushi.App.new()
        app.save()
        return app.map()

    @appier.private
    @appier.route("/apps/<app_id>", "GET")
    def show(self, app_id):
        app = pushi.App.get(map = True, app_id = app_id)
        return app

    @appier.private
    @appier.route("/apps/<app_id>", "PUT")
    def update(self, app_id):
        app = pushi.App.get(app_id = app_id)
        app.apply()
        app.save()
        return app

    @appier.private
    @appier.route("/apps/<app_id>/ping", "GET")
    def ping(self, app_id):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        self.state.trigger(app_id, "ping", "ping")

    @appier.private
    @appier.route("/apps/<app_id>/events", "POST")
    def new_event(self, app_id, data):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        _data = data.get("data", None)
        event = data.get("event", "message")
        channel = data.get("channel", "global")
        if not data: raise RuntimeError("No data set for event")
        self.state.trigger(
            app_id,
            event,
            _data,
            channels = channel,
            json_d = data,
            verify = False
        )
