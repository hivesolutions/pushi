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
import json

import ws

class PushiConnection(ws.WSConnection):

    def __init__(self, server, socket, address):
        ws.WSConnection.__init__(self, server, socket, address)
        self.socket_id = str(uuid.uuid4())
        self.channels = []

    def send_pushi(self, json_d):
        data = json.dumps(json_d)
        self.send_ws(data)

class PushiServer(ws.WSServer):

    def __init__(self, state, *args, **kwargs):
        ws.WSServer.__init__(self, *args, **kwargs)
        self.state = state
        self.sockets = {}

    def on_connection(self, connection):
        ws.WSServer.on_connection(self, connection)
        self.sockets[connection.socket_id] = connection
        self.trigger(
            "connect",
            socket_id = connection.socket_id
        )

    def on_connection_d(self, connection):
        ws.WSServer.on_connection_d(self, connection)
        del self.sockets[connection.socket_id]
        self.trigger(
            "disconnect",
            socket_id = connection.socket_id
        )

    def new_connection(self, socket, address):
        return PushiConnection(self, socket, address)

    def on_handshake(self, connection):
        ws.WSServer.on_handshake(self, connection)
        json_d = dict(
            event = "pusher:connection_established",
            data = json.dumps(dict(
                socket_id = connection.socket_id
            ))
        )
        connection.send_pushi(json_d)

    def on_data_ws(self, connection, data):
        ws.WSServer.on_data_ws(self, connection, data)

        json_d = json.loads(data)
        event = json_d.get("event", None)
        event = event.replace(":", "_")

        method_name = "handle_" + event
        method = getattr(self, method_name)
        method(connection, json_d)

    def handle_pusher_subscribe(self, connection, json_d):
        data = json_d.get("data", {})
        channel = data.get("channel", None)

        self.trigger(
            "subscribe",
            socket_id = connection.socket_id,
            channel = channel
        )

        json_d = dict(
            event = "pusher_internal:subscription_succeeded",
            data = json.dumps(dict()),
            channel =  channel
        )
        connection.send_pushi(json_d)

    def send_socket(self, socket_id, json_d):
        connection = self.sockets[socket_id]
        connection.send_pushi(json_d)

if __name__ == "__main__":
    server = PushiServer()
    server.serve()
