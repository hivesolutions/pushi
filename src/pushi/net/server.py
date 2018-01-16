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

import uuid
import json

import netius.servers

class PushiConnection(netius.servers.WSConnection):

    def __init__(self, *args, **kwargs):
        netius.servers.WSConnection.__init__(self, *args, **kwargs)
        self.app_key = None
        self.socket_id = str(uuid.uuid4())
        self.channels = []
        self.count = 0

    def send_pushi(self, json_d):
        data = json.dumps(json_d)
        self.send_ws(data)
        self.count += 1
        self.owner.count += 1

    def load_app(self):
        app_key = self.path.rsplit("/", 1)[-1]
        is_unicode = netius.legacy.is_unicode(app_key)
        if not is_unicode: app_key = app_key.decode("utf-8")
        if not app_key: raise RuntimeError("Invalid app key loaded")
        if not len(app_key) == 64: raise RuntimeError("Invalid app key length")
        self.app_key = app_key

class PushiServer(netius.servers.WSServer):

    WS_CLOSE_FRAME = b"\x03\xe9"

    def __init__(self, state = None, *args, **kwargs):
        netius.servers.WSServer.__init__(self, *args, **kwargs)
        self.state = state
        self.sockets = {}
        self.count = 0

    def info_dict(self):
        info = netius.servers.WSServer.info_dict(self)
        info["count"] = self.count
        return info

    def on_connection_c(self, connection):
        netius.servers.WSServer.on_connection_c(self, connection)
        self.sockets[connection.socket_id] = connection
        self.trigger(
            "connect",
            connection = connection,
            app_key = connection.app_key,
            socket_id = connection.socket_id
        )

    def on_connection_d(self, connection):
        netius.servers.WSServer.on_connection_d(self, connection)
        del self.sockets[connection.socket_id]
        self.trigger(
            "disconnect",
            connection = connection,
            app_key = connection.app_key,
            socket_id = connection.socket_id
        )

    def new_connection(self, socket, address, ssl = False):
        return PushiConnection(self, socket, address, ssl = ssl)

    def on_handshake(self, connection):
        netius.servers.WSServer.on_handshake(self, connection)
        connection.load_app()

        json_d = dict(
            event = "pusher:connection_established",
            data = json.dumps(dict(
                socket_id = connection.socket_id
            ))
        )
        connection.send_pushi(json_d)

    def on_data_ws(self, connection, data):
        netius.servers.WSServer.on_data_ws(self, connection, data)

        cls = self.__class__

        if not data: return
        if data == cls.WS_CLOSE_FRAME: return

        try:
            data = data.decode("utf-8")
            json_d = json.loads(data)
        except:
            raise netius.DataError("Invalid message received '%s'" % data)

        event = json_d.get("event", None)
        event = event.replace(":", "_")

        method_name = "handle_" + event
        has_method = hasattr(self, method_name)
        if has_method: method = getattr(self, method_name)
        else: method = self.handle_event
        method(connection, json_d)

    def handle_pusher_subscribe(self, connection, json_d):
        data = json_d.get("data", {})
        channel = data.get("channel", None)
        auth = data.get("auth", None)
        channel_data = data.get("channel_data", None)

        self.trigger(
            "subscribe",
            connection = connection,
            app_key = connection.app_key,
            socket_id = connection.socket_id,
            channel = channel,
            auth = auth,
            channel_data = channel_data
        )

        if not self.state: return

        data = self.state.get_channel(connection.app_key, channel)
        json_d = dict(
            event = "pusher_internal:subscription_succeeded",
            data = json.dumps(data),
            channel = channel
        )
        connection.send_pushi(json_d)

    def handle_pusher_unsubscribe(self, connection, json_d):
        data = json_d.get("data", {})
        channel = data.get("channel", None)

        self.trigger(
            "unsubscribe",
            connection = connection,
            app_key = connection.app_key,
            socket_id = connection.socket_id,
            channel = channel
        )

        if not self.state: return

        data = self.state.get_channel(connection.app_key, channel)
        json_d = dict(
            event = "pusher_internal:unsubscription_succeeded",
            data = json.dumps(data),
            channel = channel
        )
        connection.send_pushi(json_d)

    def handle_pusher_latest(self, connection, json_d):
        data = json_d.get("data", {})
        channel = data.get("channel", None)
        skip = data.get("skip", 0)
        count = data.get("count", 10)

        self.trigger(
            "validate",
            connection = connection,
            app_key = connection.app_key,
            socket_id = connection.socket_id,
            channel = channel
        )

        if not self.state: return

        data = self.state.get_channel(
            connection.app_key,
            channel,
            skip = skip,
            count = count,
            limit = False
        )
        json_d = dict(
            event = "pusher_internal:latest",
            data = json.dumps(data),
            channel = channel
        )
        connection.send_pushi(json_d)

    def handle_event(self, connection, json_d):
        data = json_d["data"]
        event = json_d["event"]
        channel = json_d["channel"]
        echo = json_d.get("echo", False)
        persist = json_d.get("persist", True)

        if not self.state: return

        app_id = self.state.app_key_to_app_id(connection.app_key)
        self.state.trigger(
            app_id,
            event,
            data,
            channels = (channel,),
            echo = echo,
            persist = persist,
            owner_id = connection.socket_id
        )

    def send_socket(self, socket_id, json_d):
        connection = self.sockets[socket_id]
        connection.send_pushi(json_d)

if __name__ == "__main__":
    server = PushiServer()
    server.serve()
else:
    __path__ = []
