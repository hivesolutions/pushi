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
import json
import hmac
import copy
import types
import hashlib
import threading

base_dir = (os.path.normpath(os.path.dirname(__file__) or ".") + "/../..")
if not base_dir in sys.path: sys.path.insert(0, base_dir)

import pushi
import appier

class AppState(object):
    """
    The state object that defined the various state variables
    for an app registered in the system. There should be one
    of this objects per each application loaded.
    """

    def __init__(self, app_id, app_key):
        self.app_id = app_id
        self.app_key = app_key
        self.socket_channels = {}
        self.channel_sockets = {}
        self.channel_info = {}
        self.channel_socket_data = {}

class State(appier.Mongo):

    def __init__(self):
        appier.Mongo.__init__(self)
        self.app = None
        self.server = None
        self.app_id_state = {}
        self.app_key_state = {}

    def load(self, app, server):
        self.app = app
        self.server = server

        self.server.bind("connect", self.connect)
        self.server.bind("disconnect", self.disconnect)
        self.server.bind("subscribe", self.subscribe)

        APP_HOST = os.environ.get("APP_HOST", "127.0.0.1")
        APP_PORT = int(os.environ.get("APP_PORT", "8080"))
        SERVER_HOST = os.environ.get("SERVER_HOST", "127.0.0.1")
        SERVER_PORT = int(os.environ.get("SERVER_PORT", "9090"))

        app_kwargs = dict(host = APP_HOST, port = APP_PORT)
        server_kwargs = dict(host = SERVER_HOST, port = SERVER_PORT)

        threading.Thread(target = self.app.serve, kwargs = app_kwargs).start()
        threading.Thread(target = self.server.serve, kwargs = server_kwargs).start()

    def connect(self, connection, app_key, socket_id):
        pass

    def disconnect(self, connection, app_key, socket_id):
        state = self.get_state(app_key = app_key)
        channels = state.socket_channels.get(socket_id, [])
        channels = copy.copy(channels)
        for channel in channels: self.unsubscribe(connection, app_key, socket_id, channel)
        if socket_id in state.socket_channels: del state.socket_channels[socket_id]

    def subscribe(self, connection, app_key, socket_id, channel, auth = None, channel_data = None):
        is_private = channel.startswith("private-") or channel.startswith("presence-")
        if is_private: self.verify(app_key, socket_id, channel, auth)

        is_presence = channel.startswith("presence-")
        if not is_presence: channel_data = None

        state = self.get_state(app_key = app_key)
        channel_socket = (channel, socket_id)

        channels = state.socket_channels.get(socket_id, [])
        channels.append(channel)
        state.socket_channels[socket_id] = channels

        sockets = state.channel_sockets.get(channel, [])
        sockets.append(socket_id)
        state.channel_sockets[channel] = sockets

        if not channel_data: return

        user_id = channel_data["user_id"]
        state.channel_socket_data[channel_socket] = channel_data

        info = state.channel_info.get(channel, {})
        users = info.get("users", {})
        conns = info.get("conns", [])
        user_count = info.get("user_count", 0)

        conns.append(connection)

        user_conns = users.get(user_id, [])
        user_conns.append(connection)
        users[user_id] = user_conns

        is_new = len(user_conns) == 1
        if is_new: user_count += 1

        info["users"] = users
        info["conns"] = conns
        info["user_count"] = user_count
        state.channel_info[channel] = info

        if not is_new: return

        json_d = dict(
            event = "pusher:member_added",
            member = json.dumps(channel_data),
            channel =  channel
        )

        for _connection in conns:
            if _connection == connection: continue
            _connection.send_pushi(json_d)

    def unsubscribe(self, connection, app_key, socket_id, channel):
        state = self.get_state(app_key = app_key)
        channel_socket = (channel, socket_id)

        channels = state.socket_channels.get(socket_id, [])
        if channel in channels: channels.remove(channel)

        sockets = state.channel_sockets.get(channel, [])
        if socket_id in sockets: sockets.remove(socket_id)

        channel_data = state.channel_socket_data.get(channel_socket)
        if not channel_data: return

        del state.channel_socket_data[channel_socket]

        user_id = channel_data["user_id"]

        info = state.channel_info.get(channel, {})
        users = info.get("users", {})
        conns = info.get("conns", [])
        user_count = info.get("user_count", 0)

        conns.remove(connection)

        user_conns = users.get(user_id, [])
        user_conns.remove(connection)
        users[user_id] = user_conns

        is_old = len(user_conns) == 0
        if is_old: del users[user_id]; user_count -= 1

        info["users"] = users
        info["conns"] = conns
        info["user_count"] = user_count
        state.channel_info[channel] = info

        if not is_old: return

        is_empty = len(conns) == 0
        if is_empty: del state.channel_info[channel]

        json_d = dict(
            event = "pusher:member_removed",
            member = json.dumps(channel_data),
            channel =  channel
        )

        for _connection in conns:
            if _connection == connection: continue
            _connection.send_pushi(json_d)

    def trigger(self, app_id, event, data, channels = None, owner_id = None):
        if not channels: channels = ("global",)
        for channel in channels: self.trigger_c(
            app_id,
            channel,
            event,
            data,
            owner_id = owner_id
        )

    def trigger_c(self, app_id, channel, event, data, owner_id = None):
        data_t = type(data)
        data = data if data_t in types.StringTypes else json.dumps(data)

        json_d = dict(
            channel = channel,
            event = event,
            data = data
        )
        self.send_channel(app_id, channel, json_d, owner_id = owner_id)

    def send_channel(self, app_id, channel, json_d, owner_id = None):
        state = self.get_state(app_id = app_id)
        if owner_id: self.verify_presence(app_id, owner_id, channel)
        sockets = state.channel_sockets.get(channel, [])
        for socket_id in sockets:
            if socket_id == owner_id: continue
            self.send_socket(socket_id, json_d)

    def send_socket(self, socket_id, json_d):
        self.server.send_socket(socket_id, json_d)

    def get_state(self, app_id = None, app_key = None):
        state = None

        if not app_id and not app_key:
            raise RuntimeError("No app identifier was provided")

        if app_id: state = self.app_id_state.get(app_id, None)
        if app_key: state = self.app_key_state.get(app_key, None)

        if state: return state

        app = self.get_app(app_id = app_id, app_key = app_key)
        if not app: raise RuntimeError("No app found for the provided parameters")

        app_id = app["app_id"]
        app_key = app["key"]

        state = AppState(app_id, app_key)
        self.app_id_state[app_id] = state
        self.app_key_state[app_key] = state

        return state

    def get_app(self, app_id = None, app_key = None):
        db = self.get_db("pushi")
        if app_id: app = db.app.find_one(dict(app_id = app_id))
        if app_key: app = db.app.find_one(dict(key = app_key))
        return app

    def verify(self, app_key, socket_id, channel, auth):
        app = self.get_app(app_key = app_key)
        app_secret = app["secret"]

        string = "%s:%s" % (socket_id, channel)
        structure = hmac.new(str(app_secret), str(string), hashlib.sha256)
        digest = structure.hexdigest()
        auth_v = "%s:%s" % (app_key, digest)

        if not auth == auth_v: raise RuntimeError("Invalid signature")

    def verify_presence(self, app_id, socket_id, channel):
        state = self.get_state(app_id = app_id)
        channels = state.socket_channels.get(socket_id, [])
        if not channel in channels:
            raise RuntimeError("Socket '%s' is not allowed for '%s'" % (socket_id, channel))

    def app_id_to_app_key(self, app_id):
        state = self.get_state(app_id = app_id)
        return state.app_key

    def app_key_to_app_id(self, app_key):
        state = self.get_state(app_key = app_key)
        return state.app_id

if __name__ == "__main__":
    state = State()
    app = pushi.PushiApp(state)
    server = pushi.PushiServer(state)
    state.load(app, server)
