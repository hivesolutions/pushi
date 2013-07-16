#!/usr/bin/python
# -*- coding: utf-8 -*-

import pushi

class State(object):

    app = None

    server = None

    socket_channels = {}

    channel_sockets = {}

    @staticmethod
    def connect(socket_id):
        pass

    @staticmethod
    def disconnect(socket_id):
        pass

    @staticmethod
    def subscribe(socket_id, channel):
        channels = State.socket_channels.get(socket_id)
        channels.append(channel)

        sockets = State.channel_sockets.get(channel)
        sockets.append(socket_id)

    @staticmethod
    def unsubscribe(socket_id, channel):
        pass

if __name__ == "__main__":
    State.server = pushi.PushiServer()
    State.server.serve()
