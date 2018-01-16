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

class PushiEvent(base.PushiBase):

    mid = appier.field(
        index = True,
        immutable = True,
        default = True,
        description = "MID"
    )

    channel = appier.field(
        index = True,
        immutable = True
    )

    owner_id = appier.field(
        immutable = True,
        description = "Owner ID"
    )

    timestamp = appier.field(
        type = float,
        immutable = True,
        meta = "datetime"
    )

    data = appier.field(
        type = dict,
        immutable = True,
        meta = "longtext"
    )

    @classmethod
    def validate(cls):
        return super(PushiEvent, cls).validate() + [
            appier.not_null("mid"),
            appier.not_empty("mid"),

            appier.not_null("channel"),
            appier.not_empty("channel"),

            appier.not_null("timestamp")
        ]

    @classmethod
    def list_names(cls):
        return ["mid", "channel", "owner_id", "timestamp"]

    def pre_save(self):
        base.PushiBase.pre_save(self)
        appier.verify(not "mid" in self.data)
        appier.verify(not "timestamp" in self.data)
