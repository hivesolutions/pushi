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

from . import base

class Web(base.PushiBase):

    url = appier.field(
        index = True,
        description = "URL"
    )

    event = appier.field(
        index = True
    )

    @classmethod
    def validate(cls):
        return super(Web, cls).validate() + [
            appier.not_null("url"),
            appier.not_empty("url"),

            appier.not_null("event"),
            appier.not_empty("event")
        ]

    @classmethod
    def list_names(cls):
        return ["url", "event"]

    def pre_update(self):
        base.PushiBase.pre_update(self)
        previous = self.__class__.get(id = self.id)
        self.state and self.state.web_handler.remove(
            previous.app_id,
            previous.url,
            previous.event
        )

    def post_create(self):
        base.PushiBase.pre_create(self)
        self.state and self.state.web_handler.add(
            self.app_id,
            self.url,
            self.event
        )

    def post_update(self):
        base.PushiBase.post_update(self)
        self.state and self.state.web_handler.add(
            self.app_id,
            self.url,
            self.event
        )

    def post_delete(self):
        base.PushiBase.post_delete(self)
        self.state and self.state.web_handler.remove(
            self.app_id,
            self.url,
            self.event
        )
