#!/usr/bin/python
# -*- coding: utf-8 -*-

import ws

class EchoServer(ws.WSServer):

    def on_data_ws(self, connection, data):
        ws.WSServer.on_data_ws(self, connection, data)
        connection.send_ws(data)

if __name__ == "__main__":
    server = EchoServer()
    server.serve()
