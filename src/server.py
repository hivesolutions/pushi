#!/usr/bin/python
# -*- coding: utf-8 -*-

import errno
import socket
import base64
import select
import hashlib

CHUNK_SIZE = 4096
""" The size of the chunk to be used while received
data from the service socket """

WSAEWOULDBLOCK = 10035
""" The wsa would block error code meant to be used on
windows environments as a replacement for the would block
error code that indicates the failure to operate on a non
blocking connection """

class Connection(object):

    def __init__(self, server, socket, address):
        self.server = server
        self.socket = socket
        self.address = address

    def open(self):
        server = self.server

        server.read.append(self.socket)
        server.write.append(self.socket)
        server.error.append(self.socket)

        server.connections.append(self)
        server.connections_m[self.socket] = self

    def close(self):
        server = self.server

        server.read.remove(self.socket)
        server.write.remove(self.socket)
        server.error.remove(self.socket)

        server.connections.remove(self)
        del server.connections_m[self.socket]

    def send(self, data):
        self.socket.send(data)

    def recv(self, size = CHUNK_SIZE):
        return self.socket.recv(size)

class WSConnection(Connection):

    def __init__(self, server, socket, address):
        Connection.__init__(self, server, socket, address)
        self.handshake = False
        self.buffer_l = []
        self.headers = {}

    def send_ws(self, data):
        encoded = self._encode(data)
        return self.send(encoded)

    def recv_ws(self, size = CHUNK_SIZE):
        data = self.recv(size = size)
        decoded = self._decode(data)
        return decoded

    def add_buffer(self, data):
        self.buffer_l.append(data)

    def do_handshake(self):
        if self.handshake:
            raise RuntimeError("Handshake already done")

        buffer = "".join(self.buffer_l)
        if not buffer[-4:] == "\r\n\r\n":
            raise RuntimeError("Missing data for handshake")

        lines = buffer.split("\r\n")
        for line in lines[1:]:
            values = line.split(":")
            values_l = len(values)
            if not values_l == 2: continue

            key, value = values
            key = key.strip()
            value = value.strip()
            self.headers[key] = value

        self.handshake = True

    def accept_key(self):
        socket_key = self.headers.get("Sec-WebSocket-Key", None)
        if not socket_key:
            raise RuntimeError("No socket key found in headers")

        hash = hashlib.sha1(socket_key + WSServer.MAGIC_VALUE)
        hash_digest = hash.digest()
        accept_key = base64.b64encode(hash_digest)
        return accept_key

    def _encode(self, data):
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

    def _decode(self, data):
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

class Server(object):

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
        self.on_socket_c(socket_c, address)

    def on_write_s(self, socket):
        pass

    def on_error_s(self, socket):
        pass

    def on_read(self, _socket):
        connection = self.connections_m[_socket]
        
        try:
            while True:
                data = _socket.recv(CHUNK_SIZE)
                if data:
                    self.on_data(connection, data)
                else:
                    self.on_connection_d(connection)
                    break
        except socket.error, error:
            if not error.args[0] in (errno.EWOULDBLOCK, errno.EAGAIN, errno.EPERM, errno.ENOENT, WSAEWOULDBLOCK):
                connection.close()
        except BaseException:
            connection.close()

    def on_write(self, socket):
        pass

    def on_error(self, socket):
        pass

    def on_data(self, connection, data):
        pass

    def on_socket_c(self, socket_c, address):
        socket_c.setblocking(0)
        socket_c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

        connection = self.new_connection(socket_c, address)
        self.on_connection(connection)

    def on_socket_d(self, socket_c):
        connection = self.connections_m.get(socket_c, None)
        if not connection: return

    def on_connection(self, connection):
        connection.open()

    def on_connection_d(self, connection):
        connection.close()

    def new_connection(self, socket, address):
        return Connection(self, socket, address)

class WSServer(Server):

    MAGIC_VALUE = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    """ The magic value used by the websocket protocol as part
    of the key generation process in the handshake """

    def on_connection(self, connection):
        Server.on_connection(self, connection)

    def on_data(self, connection, data):
        Server.on_data(self, connection, data)

        if connection.handshake:
            decoded = connection._decode(data)
            self.on_data_ws(connection, decoded)

        else:
            connection.add_buffer(data)
            connection.do_handshake()
            accept_key = connection.accept_key()
            response = self._handshake_response(accept_key)
            connection.send(response)

    def new_connection(self, socket, address):
        return WSConnection(self, socket, address)

    def send_ws(self, connection, data):
        encoded = self._encode(data)
        connection.send(encoded)

    def on_data_ws(self, connection, data):
        pass

    def _handshake_response(self, accept_key):
        """
        Returns the response contents of the handshake operation for
        the provided accept key.

        The key value should already be calculated according to the
        specification.

        @type accept_key: String
        @param accept_key: The accept key to be used in the creation
        of the response message.
        @rtype: String
        @return: The response message contents generated according to
        the specification and the provided accept key.
        """

        data = "HTTP/1.1 101 Switching Protocols\r\n" +\
            "Upgrade: websocket\r\n" +\
            "Connection: Upgrade\r\n" +\
            "Sec-WebSocket-Accept: %s\r\n\r\n" % accept_key
        return data

class EchoServer(WSServer):

    def on_data_ws(self, connection, data):
        WSServer.on_data_ws(self, connection, data)
        connection.send_ws(data)

if __name__ == "__main__":
    server = EchoServer()
    server.serve()
