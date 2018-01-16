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

class AppAPI(object):

    def create_app(self, name):
        # runs the post call that will create the app with the provided
        # name then returns the returning map to the caller method, it
        # should contain the generated information for the app
        result = self.post(
            self.base_url + "apps",
            auth = False,
            data_j = dict(
                name = name
            )
        )
        return result

    def update_app(self, app_id = None, **kwargs):
        # retrieves the proper app id to be used defaulting to the current
        # defined app id in case none is provided
        app_id = app_id or self.app_id

        # runs the pit call that will create the app with the provided
        # name then returns the returning map to the caller method, it
        # should contain the newly updated information for the app
        result = self.put(
            self.base_url + "apps/%s" % app_id,
            data_j = kwargs
        )
        return result
