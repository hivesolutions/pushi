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

import threading

OPEN = 1
""" The open status value, meant to be used in situations
where the status of the entity is open (opposite of closed) """

CLOSED = 2
""" Closed status value to be used in entities which have
no pending structured opened and operations are limited """

CHUNK_SIZE = 4096
""" The size of the chunk to be used while received
data from the service socket """

class Connection(object):
    """
    Abstract connection object that should encapsulate
    a socket object enabling it to be accessed in much
    more "protected" way avoiding possible sync problems.

    It should also abstract the developer from all the
    select associated complexities adding and removing the
    underlying socket from the selecting mechanism for the
    appropriate operations.
    """

    def __init__(self, server, socket, address):
        self.status = CLOSED
        self.server = server
        self.socket = socket
        self.address = address
        self.pending = []
        self.pending_lock = threading.RLock()

    def open(self):
        # in case the current status of the connection is not
        # closed does not make sense to open it as it should
        # already be open anyway (returns immediately)
        if not self.status == CLOSED: return

        # retrieves the reference to the owner server from the
        # current instance to be used to add the socket to the
        # proper pooling mechanisms (at least for reading)
        server = self.server

        # registers the socket for the proper reading mechanisms
        # in the polling infra-structure of the server
        server.read_l.append(self.socket)
        server.error_l.append(self.socket)

        # adds the current connection object to the list of
        # connections in the server and the registers it in
        # the map that associates the socket with the connection
        server.connections.append(self)
        server.connections_m[self.socket] = self

        # sets the status of the current connection as open
        # as all the internal structures have been correctly
        # updated and not it's safe to perform operations
        self.status = OPEN

    def close(self):
        # in case the current status of the connection is not open
        # doen't make sense to close as it's already closed
        if not self.status == OPEN: return

        # immediately sets the status of the connection as closed
        # so that no one else changed the current connection status
        # this is relevant to avoid any erroneous situation
        self.status = CLOSED

        server = self.server

        if self.socket in server.read_l: server.read_l.remove(self.socket)
        if self.socket in server.write_l: server.write_l.remove(self.socket)
        if self.socket in server.error_l: server.error_l.remove(self.socket)

        if self in server.connections: server.connections.remove(self)
        if self.socket in server.connections_m: del server.connections_m[self.socket]

        try: self.socket.close()
        except: pass

    def ensure_write(self):
        if not self.status == OPEN: return
        if self.socket in self.server.write_l: return
        self.server.write_l.append(self.socket)

    def remove_write(self):
        if not self.status == OPEN: return
        if not self.socket in self.server.write_l: return
        self.server.write_l.remove(self.socket)

    def send(self, data):
        """
        The main send call to be used by a proxy connection and
        from different threads.

        Calling this method should be done with care as this can
        create dead lock or socket corruption situations.

        @type data: String
        @param data: The buffer containing the data to be sent
        through this connection to the other endpoint.
        """

        self.ensure_write()
        self.pending_lock.acquire()
        try: self.pending.insert(0, data)
        finally: self.pending_lock.release()

    def recv(self, size = CHUNK_SIZE):
        return self._recv(size = size)

    def is_open(self):
        return self.status == OPEN

    def is_closed(self):
        return self.status == CLOSED

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
