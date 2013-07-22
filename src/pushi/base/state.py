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
import types
import threading

import pushi

class State(object):

    app = None

    server = None

    socket_channels = {}

    channel_sockets = {}

    def __init__(self):
        self.app = None
        self.server = None
        self.socket_channels = {}
        self.channel_sockets = {}

    def load(self, app, server):
        self.app = app
        self.server = server

        self.server.bind("connect", self.connect)
        self.server.bind("disconnect", self.disconnect)
        self.server.bind("subscribe", self.subscribe)

        threading.Thread(target = self.app.serve).start()
        threading.Thread(target = self.server.serve).start()

    def connect(self, socket_id):
        pass

    def disconnect(self, socket_id):
        channels = self.socket_channels.get(socket_id, [])
        for channel in channels: self.unsubscribe(socket_id, channel)

    def subscribe(self, socket_id, channel):
        channels = self.socket_channels.get(socket_id, [])
        channels.append(channel)
        self.socket_channels[socket_id] = channels

        sockets = self.channel_sockets.get(channel, [])
        sockets.append(socket_id)
        self.channel_sockets[channel] = sockets

    def unsubscribe(self, socket_id, channel):
        channels = self.socket_channels.get(socket_id, [])
        if channel in channels: channels.remove(channel)

        sockets = self.channel_sockets.get(channel, [])
        if socket_id in sockets: sockets.remove(socket_id)

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
