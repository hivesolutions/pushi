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
    @appier.route("/apps/<app_id>/subscriptions_web", "GET")
    def subscriptions_web(self, app_id, user_id = None, event = None):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        web_handler = self.state.web_handler
        return web_handler.subscriptions(app_id)

    @appier.private
    @appier.route("/apps/<app_id>/subscribe_web", "GET")
    def subscribe_web(self, app_id, url, event, auth = None, unsubscribe = True):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        web_handler = self.state.web_handler
        web_handler.subscribe(
            app_id,
            url,
            event,
            auth = auth,
            unsubscribe = unsubscribe
        )

    @appier.private
    @appier.route("/apps/<app_id>/unsubscribe_web", "GET")
    def unsubscribe_web(self, app_id, url, event = None):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        web_handler = self.state.web_handler
        web_handler.unsubscribe(
            app_id,
            url,
            event = event
        )

    @appier.private
    @appier.route("/apps/<app_id>/events", "GET")
    def list_events(self, app_id, count = 10):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        db = self.get_db("pushi")
        limit = int(count)
        cursor = db.event.find(
            app_id = app_id,
            limit = limit,
            sort = [("_id", -1),]
        )
        events = [event for event in cursor]
        for event in events: del event["_id"]
        return dict(
            events = events
        )

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

    @appier.private
    @appier.route("/apps/<app_id>/sockets", "GET")
    def list_sockets(self, app_id):
        state = self.state.get_state(app_id = app_id)

        sockets = []

        for socket_id, channel in state.socket_channels.iteritems():
            socket = dict(socket_id = socket_id, channel = channel)
            sockets.append(socket)

        return dict(
            sockets = sockets
        )

    @appier.private
    @appier.route("/apps/<app_id>/sockets/<socket_id>", "GET")
    def show_socket(self, app_id, socket_id):
        state = self.state.get_state(app_id = app_id)
        channels = state.socket_channels.get(socket_id, [])

        return dict(
            channels = channels
        )
