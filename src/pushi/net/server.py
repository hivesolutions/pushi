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

import socket

from base import * #@UnusedWildImport

class Server(Base):

    def __init__(self, name = None, handler = None, *args, **kwargs):
        Base.__init__(self, name = name, hadler = handler, *args, **kwargs)
        self.socket = None
        self.host = None
        self.port = None
        self.ssl = False

    def serve(self, host = "127.0.0.1", port = 9090, ssl = False, key_file = None, cer_file = None):
        self.set_state(STATE_CONFIG)
        self.host = host
        self.port = port
        self.ssl = ssl
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setblocking(0)
        if ssl: self.socket = self._ssl_wrap(self.socket, key_file = key_file, cer_file = cer_file)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        hasattr(socket, "SO_REUSEPORT") and\
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1) #@UndefinedVariable
        self.socket.bind((host, port))
        self.socket.listen(5)

        self.read_l.append(self.socket)
        self.write_l.append(self.socket)
        self.error_l.append(self.socket)

        self.start()

    def reads(self, reads):
        self.set_state(STATE_READ)
        for read in reads:
            if read == self.socket: self.on_read_s(read)
            else: self.on_read(read)

    def writes(self, writes):
        self.set_state(STATE_WRITE)
        for write in writes:
            if write == self.socket: self.on_write_s(write)
            else: self.on_write(write)

    def errors(self, errors):
        self.set_state(STATE_ERRROR)
        for error in errors:
            if error == self.socket: self.on_error_s(error)
            else: self.on_error(error)

    def on_read_s(self, _socket):
        try:
            socket_c, address = _socket.accept()
            try: self.on_socket_c(socket_c, address)
            except: socket_c.close(); raise
        except BaseException, exception:
            self.info(exception)
            lines = traceback.format_exc().splitlines()
            for line in lines: self.debug(line)

    def on_write_s(self, socket):
        pass

    def on_error_s(self, socket):
        pass

    def on_read(self, _socket):
        connection = self.connections_m.get(_socket, None)
        if not connection: return
        if not connection.status == OPEN: return

        try:
            # verifies if there's any pending operations in the
            # socket (eg: ssl handshaking) and performs them trying
            # to finish them, in they are still pending at the current
            # state returns immediately (waits for next loop)
            if self._pending(_socket): return

            # iterates continuously trying to read as much data as possible
            # when there's a failure to read more data it should raise an
            # exception that should be handled properly
            while True:
                data = _socket.recv(CHUNK_SIZE)
                if data: self.on_data(connection, data)
                else: self.on_connection_d(connection); break
        except ssl.SSLError, error:
            error_v = error.args[0]
            if not error_v in SSL_VALID_ERRORS:
                self.info(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.debug(line)
                self.on_connection_d(connection)
        except socket.error, error:
            error_v = error.args[0]
            if not error_v in VALID_ERRORS:
                self.info(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.debug(line)
                self.on_connection_d(connection)
        except BaseException, exception:
            self.info(exception)
            lines = traceback.format_exc().splitlines()
            for line in lines: self.debug(line)
            self.on_connection_d(connection)

    def on_write(self, socket):
        connection = self.connections_m.get(socket, None)
        if not connection: return
        if not connection.status == OPEN: return

        try:
            connection._send()
        except ssl.SSLError, error:
            error_v = error.args[0]
            if not error_v in SSL_VALID_ERRORS:
                self.info(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.debug(line)
                self.on_connection_d(connection)
        except socket.error, error:
            error_v = error.args[0]
            if not error_v in VALID_ERRORS:
                self.info(error)
                lines = traceback.format_exc().splitlines()
                for line in lines: self.debug(line)
                self.on_connection_d(connection)
        except BaseException, exception:
            self.info(exception)
            lines = traceback.format_exc().splitlines()
            for line in lines: self.debug(line)
            self.on_connection_d(connection)

    def on_error(self, socket):
        connection = self.connections_m.get(socket, None)
        if not connection: return
        if not connection.status == OPEN: return

        self.on_connection_d(connection)

    def on_data(self, connection, data):
        pass

    def on_socket_c(self, socket_c, address):
        if self.ssl: socket_c.pending = None

        socket_c.setblocking(0)
        socket_c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        socket_c.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        if self.ssl: self._ssl_handshake(socket_c)

        connection = self.new_connection(socket_c, address)
        self.on_connection_c(connection)

    def on_socket_d(self, socket_c):
        connection = self.connections_m.get(socket_c, None)
        if not connection: return

    def on_connection_c(self, connection):
        connection.open()

    def on_connection_d(self, connection):
        connection.close()
