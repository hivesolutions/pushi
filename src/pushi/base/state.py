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

import json
import hmac
import copy
import types
import hashlib
import threading

import pushi
import appier

class State(appier.Mongo):

    app = None

    server = None

    socket_channels = {}

    channel_sockets = {}

    channel_info = {}

    channel_socket_data = {}

    def __init__(self):
        appier.Mongo.__init__(self)
        self.app = None
        self.server = None
        self.socket_channels = {}
        self.channel_sockets = {}
        self.channel_socket_data = {}

    def load(self, app, server):
        self.app = app
        self.server = server

        self.server.bind("connect", self.connect)
        self.server.bind("disconnect", self.disconnect)
        self.server.bind("subscribe", self.subscribe)

        threading.Thread(target = self.app.serve).start()
        threading.Thread(target = self.server.serve).start()

    def get_app(self, app_key):
        db = self.get_db("pushi")
        app = db.app.find_one({"key" : app_key})
        return app

    def verify(self, app_key, socket_id, channel, auth):
        app = self.get_app(app_key)
        app_secret = app["secret"]

        string = "%s:%s" % (socket_id, channel)
        structure = hmac.new(str(app_secret), str(string), hashlib.sha256)
        digest = structure.hexdigest()
        auth_v = "%s:%s" % (app_key, digest)

        if not auth == auth_v: raise RuntimeError("Invalid signature")

    def connect(self, connection, app_key, socket_id):
        pass

    def disconnect(self, connection, app_key, socket_id):
        channels = self.socket_channels.get(socket_id, [])
        channels = copy.copy(channels)
        for channel in channels: self.unsubscribe(connection, app_key, socket_id, channel)

    def subscribe(self, connection, app_key, socket_id, channel, auth = None, channel_data = None):
        is_private = channel.startswith("private-") or channel.startswith("presence-")
        if is_private: self.verify(app_key, socket_id, channel, auth)

        is_presence = channel.startswith("presence-")
        if not is_presence: channel_data = None

        channel_socket = (channel, socket_id)

        channels = self.socket_channels.get(socket_id, [])
        channels.append(channel)
        self.socket_channels[socket_id] = channels

        sockets = self.channel_sockets.get(channel, [])
        sockets.append(socket_id)
        self.channel_sockets[channel] = sockets

        if not channel_data: return

        user_id = channel_data["user_id"]
        self.channel_socket_data[channel_socket] = channel_data

        info = self.channel_info.get(channel, {})
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
        self.channel_info[channel] = info

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
        channel_socket = (channel, socket_id)

        channels = self.socket_channels.get(socket_id, [])
        if channel in channels: channels.remove(channel)

        sockets = self.channel_sockets.get(channel, [])
        if socket_id in sockets: sockets.remove(socket_id)

        channel_data = self.channel_socket_data.get(channel_socket)
        if not channel_data: return

        del self.channel_socket_data[channel_socket]

        user_id = channel_data["user_id"]

        info = self.channel_info.get(channel, {})
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
        self.channel_info[channel] = info

        if not is_old: return

        is_empty = len(conns) == 0
        if is_empty: del self.channel_info[channel]

        json_d = dict(
            event = "pusher:member_removed",
            member = json.dumps(channel_data),
            channel =  channel
        )

        for _connection in conns:
            if _connection == connection: continue
            _connection.send_pushi(json_d)

    def trigger(self, event, data):
        self.trigger_c("global", event, data)

    def trigger_c(self, channel, event, data):
        data_t = type(data)
        data = data if data_t in types.StringTypes else json.dumps(data)

        json_d = dict(
            channel = channel,
            event = event,
            data = data
        )
        self.send_channel(channel, json_d)

    def send_channel(self, channel, json_d):
        sockets = self.channel_sockets.get(channel, [])
        for socket_id in sockets: self.send_socket(socket_id, json_d)

    def send_socket(self, socket_id, json_d):
        self.server.send_socket(socket_id, json_d)

if __name__ == "__main__":
    state = State()
    app = pushi.PushiApp(state)
    server = pushi.PushiServer(state)
    state.load(app, server)
