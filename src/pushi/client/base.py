#!/usr/bin/python
# -*- coding: utf-8 -*-

import websocket

def start():
    ws = websocket.create_connection("ws://localhost:9090/")
    print "Sending 'Hello, World'..."
    ws.send("Hello, World")
    print "Sent"
    print "Reeiving..."
    result =  ws.recv()
    print "Received '%s'" % result
    ws.close()
