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

from . import base


class APN(base.PushiBase):
    token = appier.field(index=True)

    event = appier.field(index=True)

    @classmethod
    def validate(cls):
        return super(APN, cls).validate() + [
            appier.not_null("token"),
            appier.not_empty("token"),
            appier.not_null("event"),
            appier.not_empty("event"),
        ]

    @classmethod
    def list_names(cls):
        return ["token", "event"]

    @classmethod
    def _underscore(cls, plural=True):
        return "apns" if plural else "apn"

    @classmethod
    def _readable(cls, plural=False):
        return "APNs" if plural else "APN"

    def pre_update(self):
        base.PushiBase.pre_update(self)
        previous = self.__class__.get(id=self.id)
        self.state and self.state.apn_handler.remove(
            previous.app_id, previous.token, previous.event
        )

    def post_create(self):
        base.PushiBase.pre_create(self)
        self.state and self.state.apn_handler.add(self.app_id, self.token, self.event)

    def post_update(self):
        base.PushiBase.post_update(self)
        self.state and self.state.apn_handler.add(self.app_id, self.token, self.event)

    def post_delete(self):
        base.PushiBase.post_delete(self)
        self.state and self.state.apn_handler.remove(
            self.app_id, self.token, self.event
        )
