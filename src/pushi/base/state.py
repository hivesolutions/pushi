#!/usr/bin/python
# -*- coding: utf-8 -*-

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

        self.server.bind("subscribe", self.subscribe)

        threading.Thread(target = self.app.serve).start()
        threading.Thread(target = self.server.serve).start()

    def connect(self, socket_id):
        pass

    def disconnect(self, socket_id):
        pass

    def subscribe(self, socket_id, channel):
        channels = self.socket_channels.get(socket_id, [])
        channels.append(channel)
        self.socket_channels[socket_id] = channels

        sockets = self.channel_sockets.get(channel, [])
        sockets.append(socket_id)
        self.channel_sockets[channel] = sockets

    def unsubscribe(self, socket_id, channel):
        pass

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
