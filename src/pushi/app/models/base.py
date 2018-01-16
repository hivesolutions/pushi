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

class PushiBase(appier_extras.admin.Base):

    instance = appier.field(
        index = True,
        safe = True,
        immutable = True
    )

    @classmethod
    def get(cls, *args, **kwargs):
        request = appier.get_request()
        app_id = request.session.get("app_id", None)
        if app_id: kwargs["instance"] = app_id
        return super(PushiBase, cls).get(cls, *args, **kwargs)

    @classmethod
    def find(cls, *args, **kwargs):
        request = appier.get_request()
        app_id = request.session.get("app_id", None)
        if app_id: kwargs["instance"] = app_id
        return super(PushiBase, cls).find(cls, *args, **kwargs)

    @classmethod
    def count(cls, *args, **kwargs):
        request = appier.get_request()
        app_id = request.session.get("app_id", None)
        if app_id: kwargs["instance"] = app_id
        return super(PushiBase, cls).count(cls, *args, **kwargs)

    @classmethod
    def exists(cls, *args, **kwargs):
        previous = cls.find(*args, **kwargs)
        return previous[0] if previous else None

    def pre_create(self):
        appier_extras.admin.Base.pre_create(self)
        if self.app_id: self.instance = self.app_id

    @property
    def state(self):
        app = appier.get_app()
        return app.state

    @property
    def app_id(self):
        if hasattr(self, "instance"): return self.instance
        request = appier.get_request()
        return request.session.get("app_id", None)

    @property
    def app_key(self):
        if not self.app_id: return None
        return self.state.app_id_to_app_key(self.app_id)
