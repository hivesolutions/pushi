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

import os
import ssl
import types
import errno
import socket
import select
import logging
import traceback
import threading

import observer

CHUNK_SIZE = 4096
""" The size of the chunk to be used while received
data from the service socket """

WSAEWOULDBLOCK = 10035
""" The wsa would block error code meant to be used on
windows environments as a replacement for the would block
error code that indicates the failure to operate on a non
blocking connection """

VALID_ERRORS = (
    errno.EWOULDBLOCK,
    errno.EAGAIN,
    errno.EPERM,
    errno.ENOENT,
    WSAEWOULDBLOCK
)
""" List containing the complete set of error that represent
non ready operations in a non blocking socket """

SSL_VALID_ERRORS = (
    ssl.SSL_ERROR_WANT_READ,
    ssl.SSL_ERROR_WANT_WRITE
)
""" The list containing the valid error in the handshake
operation of the ssl connection establishment """

OPEN = 1
""" The open status value, meant to be used in situations
where the status of the entity is open (opposite of closed) """

CLOSED = 2
""" Closed status value to be used in entities which have
no pending structured opened and operations are limited """

STATE_STOP = 1
""" The stop state value, this value is set when the service
is either in the constructed stage or when the service has been
stop normally or with an error """

STATE_START = 2
""" The start state set when the service is in the starting
stage and running, normal state """

STATE_CONFIG = 3
""" The configuration state that is set when the service is
preparing to become started and the configuration attributes
are being set according to pre-determined indications """

STATE_SELECT = 4
""" State to be used when the service is in the select part
of the loop, this is the most frequent state in an idle service
as the service "spends" most of its time in it """

STATE_READ = 5
""" Read state that is set when the connection are being read
and the on data handlers are being called, this is the part
where all the logic driven by incoming data is being called """

STATE_WRITE = 6
""" The write state that is set on the writing of data to the
connections, this is a pretty "fast" state as no logic is
associated with it """

STATE_ERRROR = 7
""" The error state to be used when the connection is processing
any error state coming from its main select operation and associated
with a certain connection (very rare) """

STATE_STRINGS = (
    "STOP",
    "START",
    "CONFIG",
    "SELECT",
    "READ",
    "WRITE",
    "ERROR"
)
""" Sequence that contains the various strings associated with
the various states for the base service, this may be used to
create an integer to string resolution mechanism """

class Connection(object):

    def __init__(self, server, socket, address):
        self.status = CLOSED
        self.server = server
        self.socket = socket
        self.address = address
        self.pending = []
        self.pending_lock = threading.RLock()

    def open(self):
        server = self.server

        server.read_l.append(self.socket)
        server.error_l.append(self.socket)

        server.connections.append(self)
        server.connections_m[self.socket] = self

        self.status = OPEN

    def close(self):
        server = self.server

        if self.socket in server.read_l: server.read_l.remove(self.socket)
        if self.socket in server.write_l: server.write_l.remove(self.socket)
        if self.socket in server.error_l: server.error_l.remove(self.socket)

        if self in server.connections: server.connections.remove(self)
        if self.socket in server.connections_m: del server.connections_m[self.socket]

        try: self.socket.close()
        except: pass

        self.status = CLOSED

    def ensure_write(self):
        if self.socket in self.server.write_l: return
        self.server.write_l.append(self.socket)

    def remove_write(self):
        if not self.socket in self.server.write_l: return
        self.server.write_l.remove(self.socket)

    def send(self, data):
        self.ensure_write()
        self.pending_lock.acquire()
        try: self.pending.insert(0, data)
        finally: self.pending_lock.release()

    def recv(self, size = CHUNK_SIZE):
        return self._recv(size = size)

    def _send(self):
        self.pending_lock.acquire()
        try:
            while True:
                if not self.pending: break
                data = self.pending.pop()
                try: self.socket.send(data)
                except: self.pending.append(data)
        finally:
            self.pending_lock.release()

        self.remove_write()

    def _recv(self, size):
        return self.socket.recv(size)

class Server(observer.Observable):

    def __init__(self, name = None, handler = None, *args, **kwargs):
        observer.Observable.__init__(self, *args, **kwargs)
        self.name = name or self.__class__.__name__
        self.handler = handler
        self.logger = None
        self.socket = None
        self.host = None
        self.port = None
        self.ssl = False
        self.read_l = []
        self.write_l = []
        self.error_l = []
        self.connections = []
        self.connections_m = {}
        self._loaded = False
        self.set_state(STATE_STOP);

    def load(self):
        if self._loaded: return

        self.load_logging();
        self._loaded = True

    def load_logging(self, level = logging.DEBUG):
        logging.basicConfig(format = "%(asctime)s [%(levelname)s] %(message)s")
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(level)
        self.handler and self.logger.addHandler(self.handler)

    def serve(self, host = "127.0.0.1", port = 9090, ssl = False, key_file = None, cer_file = None):
        self.load()

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

        self.set_state(STATE_START)

        self.info("Starting the service's \"loop\" stage")
        try: self.loop()
        except BaseException, exception:
            self.error(exception)
            lines = traceback.format_exc().splitlines()
            for line in lines: self.warning(line)
        except:
            self.critical("Critical level loop exception raised")
            lines = traceback.format_exc().splitlines()
            for line in lines: self.error(line)
        finally:
            self.info("Stopping the service's \"loop\" stage")
            self.set_state(STATE_STOP)

    def loop(self):
        while True:
            self.set_state(STATE_SELECT)
            reads, writes, errors = select.select(
                self.read_l,
                self.write_l,
                self.error_l,
                0.25
            )

            self.reads(reads)
            self.writes(writes)
            self.errors(errors)

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

    def info_dict(self):
        return dict(
            loaded = self._loaded,
            host = self.host,
            port = self.port,
            ssl = self.ssl,
            connections = len(self.connections),
            state = self.get_state_s()
        )

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

        try:
            # verifies if there's any pending operations in the
            # socket (eg: ssl handshaking) and performs them trying
            # to finish them, in they are still pending at the current
            # state returns immediately (waits for next loop)
            if self._pending(_socket): return

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

    def new_connection(self, socket, address):
        return Connection(self, socket, address)

    def debug(self, object):
        self.log(object, level = logging.DEBUG)

    def info(self, object):
        self.log(object, level = logging.INFO)

    def warning(self, object):
        self.log(object, level = logging.WARNING)

    def error(self, object):
        self.log(object, level = logging.ERROR)

    def critical(self, object):
        self.log(object, level = logging.CRITICAL)

    def log(self, object, level = logging.INFO):
        object_t = type(object)
        message = unicode(object) if not object_t in types.StringTypes else object
        self.logger.log(level, message)

    def set_state(self, state):
        self._state = state

    def get_state_s(self, lower = True):
        state_s = STATE_STRINGS[self._state - 1]
        state_s = state_s.lower() if lower else state_s
        return state_s

    def _pending(self, _socket):
        """
        Tries to perform the pending operations in the socket
        and, these operations are set in the pending variable
        of the socket structure.

        The method returns if there are still pending operations
        after this method tick.

        @type _socket: Socket
        @param _socket: The socket object to be checked for
        pending operations and that is going to be used in the
        performing of these operations.
        @rtype: bool
        @return: If there are still pending operations to be
        performed in the provided socket.
        """

        if not self.ssl or not _socket.pending: return False
        _socket.pending(_socket)
        is_pending = not _socket.pending == None
        return is_pending

    def _ssl_wrap(self, _socket, key_file = None, cer_file = None):
        dir_path = os.path.dirname(__file__)
        base_path = os.path.join(dir_path, "../../")
        base_path = os.path.normpath(base_path)
        extras_path = os.path.join(base_path, "extras")
        ssl_path = os.path.join(extras_path, "ssl")

        key_file = key_file or os.path.join(ssl_path, "server.key")
        cer_file = cer_file or os.path.join(ssl_path, "server.cer")

        socket_ssl = ssl.wrap_socket(
            _socket,
            keyfile = key_file,
            certfile = cer_file,
            server_side = True,
            do_handshake_on_connect = False
        )
        return socket_ssl

    def _ssl_handshake(self, _socket):
        try:
            _socket.do_handshake()
            _socket.pending = None
        except ssl.SSLError, error:
            error_v = error.args[0]
            if error_v in SSL_VALID_ERRORS:
                _socket.pending = self._ssl_handshake
            else: raise
