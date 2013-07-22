#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (C) 2008-2012 Hive Solutions Lda.
#
# This file is part of Hive Pushi System.
#
# Hive Pushi System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Pushi System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Pushi System. If not, see <http://www.gnu.org/licenses/>.

__author__ = "João Magalhães joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import base64
import hashlib

import base

class WSConnection(base.Connection):

    def __init__(self, server, socket, address):
        base.Connection.__init__(self, server, socket, address)
        self.handshake = False
        self.buffer_l = []
        self.headers = {}

    def send_ws(self, data):
        encoded = self._encode(data)
        return self.send(encoded)

    def recv_ws(self, size = base.CHUNK_SIZE):
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

class WSServer(base.Server):

    MAGIC_VALUE = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    """ The magic value used by the websocket protocol as part
    of the key generation process in the handshake """

    def on_connection(self, connection):
        base.Server.on_connection(self, connection)

    def on_data(self, connection, data):
        base.Server.on_data(self, connection, data)

        if connection.handshake:
            decoded = connection._decode(data)
            self.on_data_ws(connection, decoded)

        else:
            connection.add_buffer(data)
            connection.do_handshake()
            accept_key = connection.accept_key()
            response = self._handshake_response(accept_key)
            connection.send(response)
            self.on_handshake(connection)

    def new_connection(self, socket, address):
        return WSConnection(self, socket, address)

    def send_ws(self, connection, data):
        encoded = self._encode(data)
        connection.send(encoded)

    def on_data_ws(self, connection, data):
        pass

    def on_handshake(self, connection):
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
