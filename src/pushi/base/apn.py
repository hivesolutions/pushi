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
import tempfile

import netius.clients

import handler

class ApnHandler(handler.Handler):
    """
    Pushi handler (adapter) for the apple push notification
    (apn) infra-structure, so that it's possible to send
    push notification to ios/osx devices.
    """

    def __init__(self, owner):
        handler.Handler.__init__(self, owner, name = "apn")
        self.subs = {}

    def send(self, app_id, event, json_d):
        message = json_d.get("data", None)
        message = json_d.get("push_data", message)
        message = json_d.get("apn_data", message)
        if not message: raise RuntimeError("No message defined")

        app = self.owner.get_app(app_id = app_id)
        key_data = app.get("apn_key", None)
        cer_data = app.get("apn_cer", None)

        if not key_data: raise RuntimeError("No apn key defined")
        if not cer_data: raise RuntimeError("No apn certificate defined")

        path = tempfile.mkdtemp()
        key_path = os.path.join(path, "apn.key")
        cer_path = os.path.join(path, "apn.cer")

        key_file = open(key_path, "wb")
        try: key_file.write(key_data)
        finally: key_file.close()

        cer_file = open(cer_path, "wb")
        try: cer_file.write(cer_data)
        finally: cer_file.close()

        # retrieves the app key for the retrieved app by unpacking the current
        # app structure into the appropriate values
        app_key = app["key"]

        # resolves the complete set of (extra) channels for the provided
        # event assuming that it may be associated with alias, then creates
        # the complete list of event containing also the "extra" events
        extra = self.owner.get_channels(app_key, event)
        events = [event] + extra

        # retrieves the complete set of subscriptions for the current apn
        # infra-structure to be able to resolve the appropriate tokens
        subs = self.subs.get(app_id, {})

        # creates the initial list of tokens to be notified and then populates
        # the list with the various token associated with the complete set of
        # resolved events, note that a set is created at the end so that one
        # token gets notified only once (no double notifications)
        tokens = []
        for event in events:
            _tokens = subs.get(event, [])
            tokens.extend(_tokens)
        tokens = set(tokens)

        # iterates over the complete set of tokens to be notified and notifies
        # them using the current apn client infra-structure
        for token in tokens:
            apn_client = netius.clients.APNClient()
            apn_client.message(
                token,
                message = message,
                sandbox = True,
                key_file = key_path,
                cer_file = cer_path
            )

    def load(self):
        db = self.owner.get_db("pushi")
        subs = db.apn.find()
        for sub in subs:
            app_id = sub["app_id"]
            token = sub["token"]
            event = sub["event"]
            self.add(app_id, token, event)

    def add(self, app_id, token, event):
        events = self.subs.get(app_id, {})
        tokens = events.get(event, [])
        tokens.append(token)
        events[event] = tokens
        self.subs[app_id] = events

    def remove(self, app_id, token, event):
        events = self.subs.get(app_id, {})
        tokens = events.get(event, [])
        if token in tokens: tokens.remove(token)

    def subscribe(self, app_id, token, event, auth = None):
        is_private = event.startswith("private-") or\
            event.startswith("presence-") or event.startswith("peer-") or\
            event.startswith("personal-")

        app = self.owner.get_app(app_id = app_id)
        app_key = app["key"]

        is_private and self.owner.verify(app_key, token, event, auth)

        db = self.owner.get_db("pushi")
        subscription = dict(
            app_id = app_id,
            event = event,
            token = token
        )

        cursor = db.apn.find(subscription)
        values = [value for value in cursor]
        if values: return

        db.apn.insert(subscription)
        self.add(app_id, token, event)

    def unsubscribe(self, app_id, token, event):
        db = self.owner.get_db("pushi")
        subscription = dict(
            app_id = app_id,
            event = event,
            token = token
        )
        db.apn.remove(subscription)

        self.remove(app_id, token, event)
