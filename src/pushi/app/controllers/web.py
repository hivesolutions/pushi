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

class WebController(appier.Controller):

    @appier.private
    @appier.route("/webs", "GET")
    def list(self):
        url = self.field("url", None)
        event = self.field("event", None)
        return self.state.web_handler.subscriptions(url = url, event = event)

    @appier.private
    @appier.route("/webs", "POST")
    def create(self):
        auth = self.field("auth", None)
        unsubscribe = self.field("unsubscribe", False, cast = bool)
        web = pushi.Web.new()
        web = self.state.web_handler.subscribe(
            web,
            auth = auth,
            unsubscribe = unsubscribe
        )
        return web.map()

    @appier.private
    @appier.route("/webs/<url>", "DELETE")
    def deletes(self, url):
        webs = self.state.web_handler.unsubscribes(url)
        return dict(
            subscriptions = [web.map() for web in webs]
        )

    @appier.private
    @appier.route("/webs/<url>/<regex('[\.\w-]+'):event>", "DELETE")
    def delete(self, url, event):
        force = self.field("force", False, cast = bool)
        web = self.state.web_handler.unsubscribe(url, event = event, force = force)
        return web.map()
