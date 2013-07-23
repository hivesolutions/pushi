#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (C) 2008-2012 Hive Solutions Lda.
#
# This file is part of Hive Pushi System.
#
# Hive Pushi System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Pushi System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Pushi System. If not, see <http://www.gnu.org/licenses/>.

__author__ = "João Magalhães joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import os
import sys

base_dir = (os.path.normpath(os.path.dirname(__file__) or ".") + "/../..")
if not base_dir in sys.path: sys.path.insert(0, base_dir)

import appier

BASE_URL = "http://localhost:8080"
""" The base url to be used for the pushi service
in the call to the API endpoint """

def setup(name = "hello_app"):
    """
    Uses the current api to create the base instances
    for a testing system.

    This method should only be used for testing purposes
    and must be used with care.

    @type name: String
    @param name: The name of the app to be created upon
    this initial testing structures.
    """

    payload = dict(
        name = name
    )

    appier.post("%s/apps" % BASE_URL, data_j = payload)

def app_test(name = "hello_app"):
    payload = dict(
        name = "dummy",
        data = "hello world",
        channels = ["global"]
    )

    appier.post("%s/apps/hello/events" % BASE_URL, data_j = payload)

if __name__ == "__main__":
    setup()
