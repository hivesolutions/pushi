#!/usr/bin/python
# -*- coding: utf-8 -*-

import appier
import websocket

def app_test():
    payload = dict(
        name = "dummy",
        data = "hello world",
        channels = ["global"]
    )

    appier.post("http://localhost:8080/apps/hello/events", data_j = payload)

def ws_test():
    ws = websocket.create_connection("ws://localhost:9090/")
    print "Sending 'Hello, World'..."
    ws.send("Hello, World")
    print "Sent"
    print "Reeiving..."
    result =  ws.recv()
    print "Received '%s'" % result
    ws.close()

if __name__ == "__main__":
    app_test()
