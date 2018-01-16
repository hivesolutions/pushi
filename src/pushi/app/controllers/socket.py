#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (c) 2008-2018 Hive Solutions Lda.
#
# This file is part of Hive Pushi System.
#
# Hive Pushi System is free software: you can redistribute it and/or modify
# it under the terms of the Apache License as published by the Apache
# Foundation, either version 2.0 of the License, or (at your option) any
# later version.
#
# Hive Pushi System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# Apache License for more details.
#
# You should have received a copy of the Apache License along with
# Hive Pushi System. If not, see <http://www.apache.org/licenses/>.

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import appier

class SocketController(appier.Controller):

    @appier.private
    @appier.route("/sockets", "GET")
    def list(self):
        app_id = self.session.get("app_id", None)
        state = self.state.get_state(app_id = app_id)

        sockets = []

        for socket_id, channel in state.socket_channels.iteritems():
            socket = dict(socket_id = socket_id, channel = channel)
            sockets.append(socket)

        return dict(
            sockets = sockets
        )

    @appier.private
    @appier.route("/sockets/<socket_id>", "POST")
    def show(self, socket_id):
        app_id = self.session.get("app_id", None)
        state = self.state.get_state(app_id = app_id)
        channels = state.socket_channels.get(socket_id, [])

        return dict(
            channels = channels
        )
