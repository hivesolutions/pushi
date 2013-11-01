#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (C) 2008-2012 Hive Solutions Lda.
#
# This file is part of Hive Pushi System.
#
# Hive Pushi System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Pushi System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Pushi System. If not, see <http://www.gnu.org/licenses/>.

__author__ = "João Magalhães joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import os
import sys
import uuid
import hashlib

base_dir = (os.path.normpath(os.path.dirname(__file__) or ".") + "/../..")
if not base_dir in sys.path: sys.path.insert(0, base_dir)

import appier

class PushiApp(appier.App, appier.Mongo):

    def __init__(self, state = None):
        appier.App.__init__(self, name = "pushi")
        appier.Mongo.__init__(self)
        self.state = state

    def auth(self, app_id, app_key, app_secret, **kwargs):
        db = self.get_db("pushi")
        app = db.app.find_one(dict(
            app_id = app_id,
            key = app_key,
            secret = app_secret
        ))
        if not app: raise RuntimeError("Invalid credentials provided")

    def info(self, data = {}):
        info = appier.App.info(self, data)
        server = self.state.server
        info["service"] = server.info_dict()
        return info

    def on_login(self, sid, secret, app_id, app_key, app_secret, **kwargs):
        appier.App.on_login(self, sid, secret, **kwargs)
        self.request.session["app_id"] = app_id
        self.request.session["app_key"] = app_key
        self.request.session["app_secret"] = app_secret

    def on_logout(self):
        appier.App.on_logout(self)
        if not self.request.session: return
        del self.request.session["app_id"]
        del self.request.session["app_key"]
        del self.request.session["app_secret"]

    @appier.private
    @appier.route("/apps", "GET")
    def list_apps(self):
        db = self.get_db("pushi")
        apps = [app for app in db.app.find()]
        for app in apps: del app["_id"]
        return dict(
            apps = apps
        )

    @appier.route("/apps", "POST")
    def create_app(self, data):
        name = data["name"]

        db = self.get_db("pushi")
        app = db.app.find_one(dict(name = name))
        if app: raise RuntimeError("Duplicated app name")

        app_id = str(uuid.uuid4())
        key = str(uuid.uuid4())
        secret = str(uuid.uuid4())

        app_id = hashlib.sha256(app_id).hexdigest()
        key = hashlib.sha256(key).hexdigest()
        secret = hashlib.sha256(secret).hexdigest()

        app = dict(
            name = name,
            app_id = app_id,
            key = key,
            secret = secret
        )

        db.app.insert(app)
        del app["_id"]

        return app

    @appier.private
    @appier.route("/apps/<app_id>", "PUT")
    def update_app(self, app_id, data):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        db = self.get_db("pushi")
        app = db.app.find_one(dict(app_id = app_id))
        if not app: raise RuntimeError("App not found")

        if "name" in data: del data["name"]
        if "app_id" in data: del data["app_id"]
        if "key" in data: del data["key"]
        if "secret" in data : del data["secret"]

        for key, value in data.iteritems(): app[key] = value
        db.app.save(app)

    @appier.private
    @appier.route("/apps/<app_id>/ping", "GET")
    def ping_app(self, app_id):
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

    @appier.route("/apps/<app_id>/subscribe_apn", "GET")
    def subscribe_apn(self, app_id, token, event, auth = None, unsubscribe = True):
        apn_handler = self.state.apn_handler
        apn_handler.subscribe(
            app_id,
            token,
            event,
            auth = auth,
            unsubscribe = unsubscribe
        )

    @appier.route("/apps/<app_id>/unsubscribe_apn", "GET")
    def unsubscribe_apn(self, app_id, token, event = None):
        apn_handler = self.state.apn_handler
        apn_handler.unsubscribe(
            app_id,
            token,
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

if __name__ == "__main__":
    app = PushiApp()
    app.serve()
