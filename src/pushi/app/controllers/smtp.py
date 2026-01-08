#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (c) 2008-2024 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import appier

import pushi


class SMTPController(appier.Controller):
    @appier.private
    @appier.route("/smtps", "GET")
    def list(self):
        email = self.field("email", None)
        event = self.field("event", None)
        return self.state.smtp_handler.subscriptions(email=email, event=event)

    @appier.private
    @appier.route("/smtps", "POST")
    def create(self):
        auth = self.field("auth", None)
        unsubscribe = self.field("unsubscribe", False, cast=bool)
        smtp = pushi.SMTP.new()
        smtp = self.state.smtp_handler.subscribe(
            smtp, auth=auth, unsubscribe=unsubscribe
        )
        return smtp.map()

    @appier.private
    @appier.route("/smtps/<email>", "DELETE")
    def deletes(self, email):
        smtps = self.state.smtp_handler.unsubscribes(email)
        return dict(subscriptions=[smtp.map() for smtp in smtps])

    @appier.private
    @appier.route(r"/smtps/<email>/<regex('[\.\w-]+'):event>", "DELETE")
    def delete(self, email, event):
        force = self.field("force", False, cast=bool)
        smtp = self.state.smtp_handler.unsubscribe(email, event=event, force=force)
        return smtp.map()
