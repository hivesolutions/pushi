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

import pushi

class AppController(appier.Controller):

    @appier.private
    @appier.route("/apps", "GET")
    def list(self):
        apps = pushi.App.find(map = True)
        return dict(
            apps = apps
        )

    @appier.route("/apps", "POST")
    def create(self):
        app = pushi.App.new()
        app.save()
        return app.map()

    @appier.private
    @appier.route("/apps/<ident>", "GET")
    def show(self, ident):
        app = pushi.App.get(map = True, ident = ident)
        return app

    @appier.private
    @appier.route("/apps/<ident>", "PUT")
    def update(self, ident):
        app = pushi.App.get(ident = ident)
        app.apply()
        app.save()
        return app

    @appier.private
    @appier.route("/apps/ping", "GET")
    def ping(self):
        app = pushi.App.get()
        self.state.trigger(app.id, "ping", "ping", persist = False)
