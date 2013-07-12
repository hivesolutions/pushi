#!/usr/bin/python
# -*- coding: utf-8 -*-

import socket
import base64
import hashlib
import select

class Connection(object):

    def __init__(self, socket, address):
        self.socket = socket
        self.address = address

class WSConnection(Connection):

    def __init__(self, socket, address):
        Connection.__init__(self, socket, address)
        self.handshake = False

class Server(object):

    CHUNK_SIZE = 4096
    """ The size of the chunk to be used while received
    data from the service socket """

    def __init__(self, *args, **kwargs):
        self.socket = None
        self.read = []
        self.write = []
        self.error = []
        self.connections = []
        self.connections_m = {}

    def serve(self, host = "127.0.0.1", port = 9090):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(0)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.socket.bind((host, port))
        self.socket.listen(5)

        self.read.append(self.socket)
        self.write.append(self.socket)
        self.error.append(self.socket)

        while True:
            reads, writes, errors = select.select(self.read, self.write, self.error)

            for read in reads:
                if read == self.socket: self.on_read_s(read)
                else: self.on_read(read)

            for write in writes:
                if write == self.socket: self.on_write_s(write)
                else: self.on_write(write)

            for error in errors:
                if error == self.socket: self.on_error_s(error)
                else: self.on_error(error)

    def on_read_s(self, _socket):
        socket_c, address = _socket.accept()

        print "new connection " + str(address)

        socket_c.setblocking(0)
        socket_c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        self.read.append(socket_c)
        self.write.append(socket_c)
        self.error.append(socket_c)

        connection = self.new_connection(socket_c, address)
        self.on_connection(connection)

    def on_write_s(self, socket):
        pass

    def on_error_s(self, socket):
        pass

    def on_read(self, socket):
        try:
            connection = self.connections_m[socket]
            while True:
                data = socket.recv(Server.CHUNK_SIZE)
                self.ondata(connection, data)
        except BaseException, exception:
            print exception

    def on_write(self, socket):
        pass

    def on_error(self, socket):
        pass
    
    def on_data(self, connection, data):
        pass

    def on_connection(self, connection):
        self.connections.append(connection)
        self.connections_m[connection.socket] = connection

    def new_connection(self, socket, address):
        return Connection(socket, address)

class WSServer(Server):

    MAGIC_VALUE = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    """ The magic value used by the websocket protocol as part
    of the key generation process in the handshake """

    def on_connection(self, connection):
        Server.on_connection(self, connection)

    def on_data(self, connection, data):
        Server.on_data(self, connection, data)
        print data

    def new_connection(self, socket, address):
        return WSConnection(socket, address)

    def send_ws(self, data):
        encoded = self.encode(data)
        self.socket.send(encoded)

    def encode(self, data):
        data_l = len(data)
        encoded_l = list()

        encoded_l.append(chr(129))

        if data_l <= 125:
            encoded_l.append(chr(data_l))

        elif data_l >= 126 and data_l <= 65535:
            encoded_l.append(chr(126))
            encoded_l.append(chr((data_l >> 8) & 255))
            encoded_l.append(chr(data_l & 255))

        else:
            encoded_l.append(chr(127))
            encoded_l.append(chr((data_l >> 56) & 255))
            encoded_l.append(chr((data_l >> 48) & 255))
            encoded_l.append(chr((data_l >> 40) & 255))
            encoded_l.append(chr((data_l >> 32) & 255))
            encoded_l.append(chr((data_l >> 24) & 255))
            encoded_l.append(chr((data_l >> 16) & 255))
            encoded_l.append(chr((data_l >> 8) & 255))
            encoded_l.append(chr(data_l & 255))

        encoded_l.append(data)
        encoded = "".join(encoded_l)
        return encoded

    def decode(self, data):
        second_byte = data[1]

        length = ord(second_byte) & 127

        index_mask_f = 2

        if length == 126: index_mask_f = 4
        elif length == 127: index_mask_f = 10

        masks = data[index_mask_f:index_mask_f + 4]

        index_data_f = index_mask_f + 4

        decoded_length = len(data) - index_data_f
        decoded_a = bytearray(decoded_length)

        i = index_data_f
        for j in range(decoded_length):
            decoded_a[j] = chr(ord(data[i]) ^ ord(masks[j % 4]))
            i += 1

        decoded = str(decoded_a)
        return decoded

    def serve_old(self, host = "127.0.0.1", port = 9090):
        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket.bind((host, port))

        # @todo must do this in an async fashion
        _socket.listen(1)

        connection, _address = _socket.accept()
        data = connection.recv(123123123)

        lines = data.split("\r\n")
        headers = {}
        for line in lines[1:]:
            values = line.split(":")
            values_l = len(values)
            key = values[0]
            value = values[1] if values_l > 1 else ""
            key = key.strip()
            value = value.strip()
            headers[key] = value

        socket_key = headers.get("Sec-WebSocket-Key", None)
        accept_key = base64.b64encode(hashlib.sha1(socket_key + WSServer.MAGIC_VALUE).digest())

        data = "HTTP/1.1 101 Switching Protocols\r\n" +\
        "Upgrade: websocket\r\n" +\
        "Connection: Upgrade\r\n" +\
        "Sec-WebSocket-Accept: %s\r\n\r\n" % accept_key
        connection.send(data)

        data = connection.recv(10000)
        received = self.decode(data)
        connection.send(self.encode(received))
        connection.send(self.encode(received))
        connection.send(self.encode(received))
        connection.send(self.encode(received))
        connection.send(self.encode(received))
        connection.send(self.encode(received))
        connection.send(self.encode(received))

        import time
        time.sleep(100)

class EchoServer(WSServer):

    def on_data(self, data):
        self.send_ws(data)

if __name__ == "__main__":
    server = EchoServer()
    server.serve()
