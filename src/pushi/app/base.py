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

import appier

class PushiApp(appier.App):

    def __init__(self, state):
        appier.App.__init__(self, name = "pushi")
        self.state = state

    @appier.route("/hello/<message>")
    def hello(self, message):
        message = "hello world %s" % message
        self.state.trigger("message", message)
        return dict(message = message.strip())

    @appier.route("/apps/<app_id>/events", "POST")
    def event(self, app_id, data):
        print app_id
        print data

if __name__ == "__main__":
    app = PushiApp()
    app.serve()
