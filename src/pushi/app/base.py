#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (C) 2008-2015 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2015 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import appier
import appier_extras

import pushi

class PushiApp(appier.App):

    def __init__(self, state = None):
        appier.App.__init__(
            self,
            name = "pushi",
            parts = (
                appier_extras.AdminPart,
            )
        )
        self.state = state

    def auth(self, app_id, app_key, app_secret, **kwargs):
        app = pushi.App.get(
            ident = app_id,
            key = app_key,
            secret = app_secret
        )
        if not app: raise RuntimeError("Invalid credentials provided")

    def info(self, data = {}):
        info = appier.App.info(self, data)
        if not self.state: return info
        server = self.state.server
        info["service"] = server.info_dict()
        return info

    def on_login(self, sid, secret, app_id, app_key, app_secret, **kwargs):
        appier.App.on_login(self, sid, secret, **kwargs)
        self.session["app_id"] = app_id
        self.session["app_key"] = app_key
        self.session["app_secret"] = app_secret

    def on_logout(self):
        appier.App.on_logout(self)
        if not self.session: return
        if "app_id" in self.session: del self.session["app_id"]
        if "app_key" in self.session: del self.session["app_key"]
        if "app_secret" in self.session: del self.session["app_secret"]

if __name__ == "__main__":
    app = PushiApp()
    app.serve()
