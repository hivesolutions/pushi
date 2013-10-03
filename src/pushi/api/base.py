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
import hmac
import hashlib

import appier

BASE_URL = "https://puxiapp.com:9090"
""" The base url to be used by the api to access
the remote endpoints, should not be changed """

class Pushi:

    def __init__(self, app_id = None, app_key = None, app_secret = None, base_url = BASE_URL):
        self.app_id = app_id or os.environ.get("PUSHI_ID", None)
        self.app_key = app_key or os.environ.get("PUSHI_KEY", None)
        self.app_secret = app_secret or os.environ.get("PUSHI_SECRET", None)
        self.base_url = base_url
        self.token = None

    def authenticate(self, channel, socket_id):
        # creates the string to hashed using both the provided
        # socket id and channel (concatenation)
        string = "%s:%s" % (socket_id, channel)

        # runs the hmac encryption in the provided secret and
        # the constructed string and returns a string containing
        # both the key and the hexadecimal digest
        structure = hmac.new(self.app_secret, string, hashlib.sha256)
        digest = structure.hexdigest()
        return "%s:%s" % (self.app_key, digest)

    def auth_callback(self, params):
        token = self.login()
        params["sid"] = token

    def ensure_login(self):
        if self.token: return self.token
        return self.login()

    def login(self):
        # tries to login in the pushi infra-structure using the
        # login route together with the full set of auth info
        # retrieving the result map that should contain the
        # session token, to be used in further calls
        result = appier.get(
            self.base_url + "/login",
            params = dict(
                app_id = self.app_id,
                app_key = self.app_key,
                app_secret = self.app_secret
            )
        )

        # unpacks the token value from the result map and then
        # returns the token to the caller method
        self.token = result["token"]
        return self.token

    def trigger(self, channel, data, event = "message"):
        # runs the ensure login call making sure that the login token
        # is currently present in the environment, this is required
        # to perform secured remote calls
        token = self.ensure_login()

        # performs the concrete event trigger operation creating an event
        # with the provided information using a secure channel
        result = appier.post(
            self.base_url + "/apps/%s/events" % self.app_id,
            data_j = dict(
                data = data,
                event = event,
                channel = channel
            ),
            params = dict(sid = token),
            auth_callback = self.auth_callback
        )
        return result
