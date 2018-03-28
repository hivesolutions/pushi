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

import hmac
import hashlib

import appier

from . import apn
from . import app
from . import web
from . import event
from . import subscription

BASE_URL = "https://puxiapp.com:9090/"
""" The base URL to be used by the api to access
the remote endpoints, should not be changed """

BASE_WS_URL = "wss://puxiapp.com/"
""" The default base websockets url that is going
to be used in case no other value is specified """

class API(
    appier.API,
    apn.APNAPI,
    app.AppAPI,
    web.WebAPI,
    event.EventAPI,
    subscription.SubscriptionAPI
):
    """
    Base class for the construction of the pushi
    proxy object for interaction with the server
    side of the pushi system.

    Should provide the various methods that enable
    the developer to make operations for both read
    and write (create and read).
    """

    def __init__(self, *args, **kwargs):
        appier.API.__init__(self, *args, **kwargs)
        self.app_id = appier.conf("PUSHI_ID", None)
        self.app_key = appier.conf("PUSHI_KEY", None)
        self.app_secret = appier.conf("PUSHI_SECRET", None)
        self.base_url = appier.conf("PUSHI_URL", BASE_URL)
        self.app_id = kwargs.get("app_id", self.app_id)
        self.app_key = kwargs.get("app_key", self.app_key)
        self.app_secret = kwargs.get("app_secret", self.app_secret)
        self.base_url = kwargs.get("base_url", self.base_url)
        self.token = None

    def build(
        self,
        method,
        url,
        data = None,
        data_j = None,
        data_m = None,
        headers = None,
        params = None,
        mime = None,
        kwargs = None
    ):
        auth = kwargs.pop("auth", True)
        if auth: kwargs["sid"] = self.get_token()

    def get_token(self):
        if self.token: return self.token
        return self.login()

    def auth_callback(self, params, headers):
        token = self.login()
        params["sid"] = token

    def login(self):
        # tries to login in the pushi infra-structure using the
        # login route together with the full set of auth info
        # retrieving the result map that should contain the
        # session token, to be used in further calls
        result = self.get(
            self.base_url + "login",
            callback = False,
            auth = False,
            app_id = self.app_id,
            app_key = self.app_key,
            app_secret = self.app_secret
        )

        # unpacks the token value from the result map and then
        # returns the token to the caller method
        self.token = result["token"]
        return self.token

    def logout(self):
        # runs the "simplistic" call to the logout operation so
        # that the session is invalidated from the server side
        self.get(
            self.base_url + "logout"
        )

        # invalidates the currently set token so that it's no longer
        # going to be used for any kind of operation
        self.token = None

    def authenticate(self, channel, socket_id):
        # in case the app key is not defined for the current
        # instance an exception must be raised as it's not possible
        # to run the authentication process without an app key
        if not self.app_key: raise RuntimeError("No app key defined")

        # creates the string to hashed using both the provided
        # socket id and channel (concatenation)
        string = "%s:%s" % (socket_id, channel)
        string = appier.legacy.bytes(string)

        # runs the hmac encryption in the provided secret and
        # the constructed string and returns a string containing
        # both the key and the hexadecimal digest
        app_secret = appier.legacy.bytes(str(self.app_secret))
        structure = hmac.new(app_secret, string, hashlib.sha256)
        digest = structure.hexdigest()
        return "%s:%s" % (self.app_key, digest)
