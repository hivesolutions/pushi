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

BASE_URL = "http://puxiapp.com"
""" The base url to be used by the api to access
the remote endpoints, should not be changed """

token = None
""" The reference to the token value that is used
for the current session, if this value is set to
a valid value the session is considered to exist """

def authenticate(channel, socket_id, app_key = None, app_secret = None):
    # retrieves both the app key and secret either from the
    # provided arguments or the environment variables
    key = app_key or os.environ["PUSHI_KEY"]
    secret = app_secret or os.environ["PUSHI_SECRET"]

    # creates the string to hashed using both the provided
    # socket id and channel (concatenation)
    string = "%s:%s" % (socket_id, channel)

    # runs the hmac encryption in the provided secret and
    # the constructed string and returns a string containing
    # both the key and the hexadecimal digest
    structure = hmac.new(secret, string, hashlib.sha256)
    digest = structure.hexdigest()
    return "%s:%s" % (key, digest)

def ensure_login(app_id = None, app_key = None, app_secret = None):
    global token
    if token: return token
    return login(
        app_id = app_id,
        app_key = app_key,
        app_secret = app_secret
    )

def login(app_id = None, app_key = None, app_secret = None):
    global token

    # retrieves the base pushi related variable either from
    # the passed arguments or from the global environment
    id = app_id or os.environ["PUSHI_ID"]
    key = app_key or os.environ["PUSHI_KEY"]
    secret = app_secret or os.environ["PUSHI_SECRET"]

    # tries to login in the pushi infra-structure using the
    # login route together with the full set of auth info
    # retrieving the result map that should contain the
    # session token, to be used in further calls
    result = appier.get(BASE_URL + "/login", dict(
        app_id = id,
        app_key = key,
        app_secret = secret
    ))

    # unpacks the token value from the result map and then
    # returns the token to the caller method
    token = result["token"]
    return token

def trigger(channel, data, event = "message", app_id = None, app_key = None, app_secret = None):
    # retrieve the app id value either from the passed attributes
    # or from the global environment variable
    id = app_id or os.environ["PUSHI_ID"]

    # runs the ensure login call making sure that the login token
    # is currently present in the environment, this is required
    # to perform secured remote calls
    token = ensure_login(
        app_id = app_id,
        app_key = app_key,
        app_secret = app_secret
    )

    # performs the concrete event trigger operation creating an event
    # with the provided information using a secure channel
    result = appier.post(BASE_URL + "/apps/%s/events" % app_id, dict(
        data = data,
        event = event,
        channel = channel
    ), dict(sid = token))
    return result
