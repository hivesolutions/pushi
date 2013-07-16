#!/usr/bin/python
# -*- coding: utf-8 -*-

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

    def new_connection(self, socket, address):
        connection = PushiConnection(self, socket, address)
        self.sockets[connection.socket_id] = connection
        return connection

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
