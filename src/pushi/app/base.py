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

import uuid
import hashlib

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
    @appier.route("/hello/<message>")
    def hello(self, message):
        message = "hello world %s" % message
        self.state.trigger("message", message)
        return dict(message = message.strip())

    @appier.private
    @appier.route("/apps", "GET")
    def list_apps(self):
        db = self.get_db("pushi")
        apps = [app for app in db.app.find()]
        for app in apps: del app["_id"]
        return dict(
            apps = apps
        )

    @appier.private
    @appier.route("/apps", "POST")
    def create_app(self, data):
        app_id = str(uuid.uuid4())
        key = str(uuid.uuid4())
        secret = str(uuid.uuid4())

        app_id = hashlib.sha256(app_id).hexdigest()
        key = hashlib.sha256(key).hexdigest()
        secret = hashlib.sha256(secret).hexdigest()

        data["app_id"] = app_id
        data["key"] = key
        data["secret"] = secret

        db = self.get_db("pushi")
        db.app.insert(data)

        return data

    @appier.private
    @appier.route("/apps/<app_id>/events", "GET")
    def event_app_get(self, app_id, data = None, channel = "global"):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        if not data: raise RuntimeError("No data set for event")

        self.state.trigger(app_id, "message", data, channels = (channel,))

    @appier.private
    @appier.route("/apps/<app_id>/events", "POST")
    def event_app_post(self, app_id, data):
        if not app_id == self.request.session["app_id"]:
            raise RuntimeError("Not allowed for app id")

        data = data.get("data", None)
        channel = data.get("channel", "global")
        if not data: raise RuntimeError("No data set for event")

        self.state.trigger(app_id, "message", data, channels = (channel,))

if __name__ == "__main__":
    app = PushiApp()
    app.serve()
