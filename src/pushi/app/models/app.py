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

import uuid
import hashlib

import appier

from . import base

class App(base.PushiBase):

    name = appier.field(
        index = True,
        default = True
    )

    ident = appier.field(
        index = True,
        safe = True,
        immutable = True
    )

    key = appier.field(
        index = True,
        safe = True,
        immutable = True
    )

    secret = appier.field(
        index = True,
        safe = True,
        immutable = True
    )

    apn_sandbox = appier.field(
        type = bool,
        description = "APN Sandbox"
    )

    apn_key = appier.field(
        meta = "longtext",
        description = "APN Key"
    )

    apn_cer = appier.field(
        meta = "longtext",
        description = "APN Cer"
    )

    @classmethod
    def validate(cls):
        return super(App, cls).validate() + [
            appier.not_null("name"),
            appier.not_empty("name"),
            appier.not_duplicate("name", cls._name())
        ]

    @classmethod
    def list_names(cls):
        return ["name", "ident", "apn_sandbox"]

    def pre_create(self):
        base.PushiBase.pre_create(self)

        ident = appier.legacy.bytes(str(uuid.uuid4()))
        key = appier.legacy.bytes(str((uuid.uuid4())))
        secret = appier.legacy.bytes(str(uuid.uuid4()))

        self.ident = hashlib.sha256(ident).hexdigest()
        self.key = hashlib.sha256(key).hexdigest()
        self.secret = hashlib.sha256(secret).hexdigest()

        self.instance = self.ident
