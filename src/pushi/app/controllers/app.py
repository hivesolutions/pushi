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

import pushi.app.models

class AppController(appier.Controller):

    @appier.private
    @appier.route("/apps", "GET")
    def list(self):
        apps = pushi.app.models.App.find(map = True)
        return dict(
            apps = apps
        )

    @appier.route("/apps", "POST")
    def create(self):
        app = pushi.app.models.App.new()
        app.save()
        return app.map()

    @appier.private
    @appier.route("/apps/<app_id>", "PUT")
    def update(self, app_id):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        app = pushi.app.models.App.get(app_id = app_id)
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
    @appier.route("/apps/<app_id>/subscriptions", "GET")
    def subscriptions(self, app_id, user_id = None, event = None):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        db = self.get_db("pushi")
        subscription = dict(
            app_id = app_id
        )
        if user_id: subscription["user_id"] = user_id
        if event: subscription["event"] = event
        cursor = db.subs.find(subscription)
        subscriptions = [subscription for subscription in cursor]
        for subscription in subscriptions: del subscription["_id"]
        return dict(
            subscriptions = subscriptions
        )

    @appier.private
    @appier.route("/apps/<app_id>/subscribe", "GET")
    def subscribe(self, app_id, user_id, event):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        db = self.get_db("pushi")
        subscription = dict(
            app_id = app_id,
            event = event,
            user_id = user_id
        )
        cursor = db.subs.find(subscription)
        values = [value for value in cursor]
        not values and db.subs.insert(subscription)

        app_key = self.state.app_id_to_app_key(app_id)
        self.state.add_alias(app_key, "personal-" + user_id, event)

    @appier.private
    @appier.route("/apps/<app_id>/unsubscribe", "GET")
    def unsubscribe(self, app_id, event, user_id):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        db = self.get_db("pushi")
        subscription = dict(
            app_id = app_id,
            event = event,
            user_id = user_id
        )
        db.subs.remove(subscription)

        app_key = self.state.app_id_to_app_key(app_id)
        self.state.remove_alias(app_key, "personal-" + user_id, event)

    @appier.private
    @appier.route("/apps/<app_id>/subscriptions_apn", "GET")
    def subscriptions_apn(self, app_id, user_id = None, event = None):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        apn_handler = self.state.apn_handler
        return apn_handler.subscriptions(app_id)

    @appier.private
    @appier.route("/apps/<app_id>/subscribe_apn", "GET")
    def subscribe_apn(self, app_id, token, event, auth = None, unsubscribe = True):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        apn_handler = self.state.apn_handler
        apn_handler.subscribe(
            app_id,
            token,
            event,
            auth = auth,
            unsubscribe = unsubscribe
        )

    @appier.private
    @appier.route("/apps/<app_id>/unsubscribe_apn", "GET")
    def unsubscribe_apn(self, app_id, token, event = None):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        apn_handler = self.state.apn_handler
        apn_handler.unsubscribe(
            app_id,
            token,
            event = event
        )

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
