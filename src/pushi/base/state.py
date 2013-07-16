#!/usr/bin/python
# -*- coding: utf-8 -*-

import threading

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
    State.app = pushi.PushiApp()
    State.server = pushi.PushiServer()

    threading.Thread(target = State.app.serve).start()
    threading.Thread(target = State.server.serve).start()
