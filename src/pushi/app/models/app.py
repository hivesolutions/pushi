#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (C) 2008-2014 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2014 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import appier
import appier_extras

class App(appier_extras.admin.Base):

    name = appier.field(
        index = True,
        default = True
    )

    app_id = appier.field(
        index = True
    )

    key = appier.field(
        index = True
    )

    secret = appier.field(
        index = True
    )

    @classmethod
    def validate(cls):
        return super(App, cls).validate() + [
            appier.not_null("name"),
            appier.not_empty("name"),

            appier.not_null("app_id"),
            appier.not_empty("app_id"),

            appier.not_null("key"),
            appier.not_empty("key"),

            appier.not_null("secret"),
            appier.not_empty("secret")
        ]
