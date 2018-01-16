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
import appier_extras

import pushi

class PushiApp(appier.APIApp):

    def __init__(self, state = None, *args, **kwargs):
        appier.APIApp.__init__(
            self,
            name = "pushi",
            parts = (
                appier_extras.AdminPart,
            ),
            *args, **kwargs
        )
        self.state = state

    def info_dict(self):
        info = appier.APIApp.info_dict(self)
        if not self.state: return info
        server = self.state.server
        info["service"] = server.info_dict()
        return info

    def auth(self, app_id, app_key, app_secret, **kwargs):
        app = pushi.App.get(
            ident = app_id,
            key = app_key,
            secret = app_secret
        )
        if not app: raise RuntimeError("Invalid credentials provided")

    def on_login(self, sid, secret, app_id, app_key, app_secret, **kwargs):
        appier.APIApp.on_login(self, sid, secret, **kwargs)
        self.session["app_id"] = app_id
        self.session["app_key"] = app_key
        self.session["app_secret"] = app_secret

    def on_logout(self):
        appier.APIApp.on_logout(self)
        if not self.session: return
        if "app_id" in self.session: del self.session["app_id"]
        if "app_key" in self.session: del self.session["app_key"]
        if "app_secret" in self.session: del self.session["app_secret"]

if __name__ == "__main__":
    app = PushiApp()
    app.serve()
else:
    __path__ = []
