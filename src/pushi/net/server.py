#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (c) 2008-2024 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os
import time
import uuid
import json

import netius.servers

# configuration constants with defaults
MAX_CONNECTIONS_GLOBAL = int(os.environ.get("PUSHI_MAX_CONNECTIONS_GLOBAL", "10000"))
MAX_CONNECTIONS_PER_IP = int(os.environ.get("PUSHI_MAX_CONNECTIONS_PER_IP", "100"))
MAX_CONNECTIONS_PER_APP = int(os.environ.get("PUSHI_MAX_CONNECTIONS_PER_APP", "5000"))
MAX_MESSAGE_SIZE = int(os.environ.get("PUSHI_MAX_MESSAGE_SIZE", "65536"))
MAX_CHANNELS_PER_SOCKET = int(os.environ.get("PUSHI_MAX_CHANNELS_PER_SOCKET", "100"))
MAX_SOCKETS_PER_CHANNEL = int(os.environ.get("PUSHI_MAX_SOCKETS_PER_CHANNEL", "10000"))
RATE_LIMIT_MESSAGES = int(os.environ.get("PUSHI_RATE_LIMIT_MESSAGES", "60"))
RATE_LIMIT_WINDOW = int(os.environ.get("PUSHI_RATE_LIMIT_WINDOW", "60"))
MAX_CHANNEL_NAME_LENGTH = int(os.environ.get("PUSHI_MAX_CHANNEL_NAME_LENGTH", "200"))
MAX_EVENT_NAME_LENGTH = int(os.environ.get("PUSHI_MAX_EVENT_NAME_LENGTH", "200"))


class PushiConnection(netius.servers.WSConnection):
    def __init__(self, *args, **kwargs):
        netius.servers.WSConnection.__init__(self, *args, **kwargs)
        self.app_key = None
        self.socket_id = str(uuid.uuid4())
        self.channels = []
        self.count = 0
        self.message_timestamps = []
        self.remote_ip = None

    def send_pushi(self, json_d):
        data = json.dumps(json_d)
        self.send_ws(data)
        self.count += 1
        self.owner.count += 1

    def check_rate_limit(self):
        """
        Checks if the connection has exceeded the rate limit.
        Returns True if the message should be allowed, False if rate limited.
        """
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW

        # remove timestamps outside the window
        self.message_timestamps = [
            ts for ts in self.message_timestamps if ts > window_start
        ]

        # check if we've exceeded the limit
        if len(self.message_timestamps) >= RATE_LIMIT_MESSAGES:
            return False

        # record this message
        self.message_timestamps.append(now)
        return True

    def load_app(self):
        app_key = self.path.rsplit("/", 1)[-1]
        is_unicode = netius.legacy.is_unicode(app_key)
        if not is_unicode:
            app_key = app_key.decode("utf-8")
        if not app_key:
            raise RuntimeError("Invalid app key loaded")
        if not len(app_key) == 64:
            raise RuntimeError("Invalid app key length")
        self.app_key = app_key


class PushiServer(netius.servers.WSServer):
    WS_CLOSE_FRAME = b"\x03\xe9"

    def __init__(self, state=None, *args, **kwargs):
        netius.servers.WSServer.__init__(self, *args, **kwargs)
        self.state = state
        self.sockets = {}
        self.count = 0
        self.connections_by_ip = {}
        self.connections_by_app = {}

    def info_dict(self):
        info = netius.servers.WSServer.info_dict(self)
        info["count"] = self.count
        return info

    def on_connection_c(self, connection):
        netius.servers.WSServer.on_connection_c(self, connection)

        # extract the remote IP address from the connection
        remote_ip = connection.address[0] if connection.address else "unknown"
        connection.remote_ip = remote_ip

        # check global connection limit
        if len(self.sockets) >= MAX_CONNECTIONS_GLOBAL:
            self._send_error(connection, "Global connection limit exceeded")
            connection.close()
            return

        # check per-IP connection limit
        ip_count = self.connections_by_ip.get(remote_ip, 0)
        if ip_count >= MAX_CONNECTIONS_PER_IP:
            self._send_error(connection, "Per-IP connection limit exceeded")
            connection.close()
            return

        # check per-app connection limit
        app_key = connection.app_key
        if app_key:
            app_count = self.connections_by_app.get(app_key, 0)
            if app_count >= MAX_CONNECTIONS_PER_APP:
                self._send_error(connection, "Per-app connection limit exceeded")
                connection.close()
                return
            self.connections_by_app[app_key] = app_count + 1

        # track connection
        self.sockets[connection.socket_id] = connection
        self.connections_by_ip[remote_ip] = ip_count + 1

        self.trigger(
            "connect",
            connection=connection,
            app_key=connection.app_key,
            socket_id=connection.socket_id,
        )

    def on_connection_d(self, connection):
        netius.servers.WSServer.on_connection_d(self, connection)

        # clean up socket tracking
        if connection.socket_id in self.sockets:
            del self.sockets[connection.socket_id]

        # clean up IP tracking
        remote_ip = connection.remote_ip
        if remote_ip and remote_ip in self.connections_by_ip:
            self.connections_by_ip[remote_ip] -= 1
            if self.connections_by_ip[remote_ip] <= 0:
                del self.connections_by_ip[remote_ip]

        # clean up app tracking
        app_key = connection.app_key
        if app_key and app_key in self.connections_by_app:
            self.connections_by_app[app_key] -= 1
            if self.connections_by_app[app_key] <= 0:
                del self.connections_by_app[app_key]

        self.trigger(
            "disconnect",
            connection=connection,
            app_key=connection.app_key,
            socket_id=connection.socket_id,
        )

    def _send_error(self, connection, message):
        """
        Sends an error message to the connection.
        """
        json_d = dict(event="pusher:error", data=json.dumps(dict(message=message)))
        try:
            connection.send_pushi(json_d)
        except Exception:
            pass

    def build_connection(self, socket, address, ssl=False):
        return PushiConnection(self, socket, address, ssl=ssl)

    def on_handshake(self, connection):
        netius.servers.WSServer.on_handshake(self, connection)
        connection.load_app()

        json_d = dict(
            event="pusher:connection_established",
            data=json.dumps(dict(socket_id=connection.socket_id)),
        )
        connection.send_pushi(json_d)

    def on_data_ws(self, connection, data):
        netius.servers.WSServer.on_data_ws(self, connection, data)

        cls = self.__class__

        if not data:
            return
        if data == cls.WS_CLOSE_FRAME:
            return

        # check message size limit
        if len(data) > MAX_MESSAGE_SIZE:
            self._send_error(connection, "Message size exceeds limit")
            return

        # check rate limit
        if not connection.check_rate_limit():
            self._send_error(connection, "Rate limit exceeded")
            return

        try:
            data = data.decode("utf-8")
            json_d = json.loads(data)
        except Exception:
            raise netius.DataError("Invalid message received '%s'" % data)

        # validate event field exists and is a string
        event = json_d.get("event", None)
        if not event or not isinstance(event, str):
            self._send_error(connection, "Invalid or missing event field")
            return

        # validate event name length
        if len(event) > MAX_EVENT_NAME_LENGTH:
            self._send_error(connection, "Event name too long")
            return

        # sanitize event name for method dispatch (only allow alphanumeric and colon/underscore)
        if not all(c.isalnum() or c in ":_-" for c in event):
            self._send_error(connection, "Invalid characters in event name")
            return

        event = event.replace(":", "_")

        method_name = "handle_" + event
        has_method = hasattr(self, method_name)
        if has_method:
            method = getattr(self, method_name)
        else:
            method = self.handle_event
        method(connection, json_d)

    def handle_pusher_subscribe(self, connection, json_d):
        data = json_d.get("data", {})
        channel = data.get("channel", None)
        auth = data.get("auth", None)
        channel_data = data.get("channel_data", None)

        # validate channel name
        if not channel or not isinstance(channel, str):
            self._send_error(connection, "Invalid or missing channel name")
            return

        if len(channel) > MAX_CHANNEL_NAME_LENGTH:
            self._send_error(connection, "Channel name too long")
            return

        # check channel subscription limit per socket
        if len(connection.channels) >= MAX_CHANNELS_PER_SOCKET:
            self._send_error(connection, "Maximum channels per socket exceeded")
            return

        self.trigger(
            "subscribe",
            connection=connection,
            app_key=connection.app_key,
            socket_id=connection.socket_id,
            channel=channel,
            auth=auth,
            channel_data=channel_data,
        )

        if not self.state:
            return

        data = self.state.get_channel(connection.app_key, channel)
        json_d = dict(
            event="pusher_internal:subscription_succeeded",
            data=json.dumps(data),
            channel=channel,
        )
        connection.send_pushi(json_d)

    def handle_pusher_unsubscribe(self, connection, json_d):
        data = json_d.get("data", {})
        channel = data.get("channel", None)

        self.trigger(
            "unsubscribe",
            connection=connection,
            app_key=connection.app_key,
            socket_id=connection.socket_id,
            channel=channel,
        )

        if not self.state:
            return

        data = self.state.get_channel(connection.app_key, channel)
        json_d = dict(
            event="pusher_internal:unsubscription_succeeded",
            data=json.dumps(data),
            channel=channel,
        )
        connection.send_pushi(json_d)

    def handle_pusher_latest(self, connection, json_d):
        data = json_d.get("data", {})
        channel = data.get("channel", None)
        skip = data.get("skip", 0)
        count = data.get("count", 10)

        self.trigger(
            "validate",
            connection=connection,
            app_key=connection.app_key,
            socket_id=connection.socket_id,
            channel=channel,
        )

        if not self.state:
            return

        data = self.state.get_channel(
            connection.app_key, channel, skip=skip, count=count, limit=False
        )
        json_d = dict(
            event="pusher_internal:latest", data=json.dumps(data), channel=channel
        )
        connection.send_pushi(json_d)

    def handle_event(self, connection, json_d):
        # validate required fields exist
        if "data" not in json_d:
            self._send_error(connection, "Missing 'data' field in event")
            return
        if "event" not in json_d:
            self._send_error(connection, "Missing 'event' field in event")
            return
        if "channel" not in json_d:
            self._send_error(connection, "Missing 'channel' field in event")
            return

        data = json_d["data"]
        event = json_d["event"]
        channel = json_d["channel"]
        echo = json_d.get("echo", False)
        persist = json_d.get("persist", True)

        # validate channel name
        if not isinstance(channel, str) or len(channel) > MAX_CHANNEL_NAME_LENGTH:
            self._send_error(connection, "Invalid channel name")
            return

        # validate event name
        if not isinstance(event, str) or len(event) > MAX_EVENT_NAME_LENGTH:
            self._send_error(connection, "Invalid event name")
            return

        if not self.state:
            return

        app_id = self.state.app_key_to_app_id(connection.app_key)
        self.state.trigger(
            app_id,
            event,
            data,
            channels=(channel,),
            echo=echo,
            persist=persist,
            owner_id=connection.socket_id,
        )

    def send_socket(self, socket_id, json_d):
        connection = self.sockets[socket_id]
        connection.send_pushi(json_d)


if __name__ == "__main__":
    server = PushiServer()
    server.serve()
else:
    __path__ = []
