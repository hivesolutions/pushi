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

import os
import shutil
import tempfile

import netius.clients

import pushi

from . import handler

class APNHandler(handler.Handler):
    """
    Pushi handler (adapter) for the apple push notification
    (APN) infra-structure, so that it's possible to send
    push notification to iOS/OSX devices.
    """

    def __init__(self, owner):
        handler.Handler.__init__(self, owner, name = "apn")
        self.subs = {}

    def send(self, app_id, event, json_d, invalid = {}):
        # tries to retrieve the appropriate message starting from
        # the most general values to the most specific values,
        # be aware that the value may be a bit fuzzy
        message = json_d.get("data", None)
        message = json_d.get("push", message)
        message = json_d.get("apn", message)
        if not message: raise RuntimeError("No message defined")

        # retrieves the reference to the app with the defined app id
        # and extracts the APN specific values for it to be used in
        # the process of authentication
        app = self.owner.get_app(app_id = app_id)
        key_data = app.apn_key
        cer_data = app.apn_cer
        sandbox = app.apn_sandbox

        # in case no key data or certificate data is present a runtime
        # error is raised to indicate the problem
        if not key_data: raise RuntimeError("No APN key defined")
        if not cer_data: raise RuntimeError("No APN certificate defined")

        # ensures that the complete set of data is encoded as bytes, as
        # this is required for the proper writing of the file, otherwise
        # and invalid encoding would be raised for some platforms
        key_data = netius.legacy.bytes(key_data)
        cer_data = netius.legacy.bytes(cer_data)

        # creates a new temporary directory that will be used to store
        # the temporary key and certificate files for ssl
        path = tempfile.mkdtemp()

        # creates the full paths to both the key and certificate
        # files using the temporary path as base
        key_path = os.path.join(path, "apn.key")
        cer_path = os.path.join(path, "apn.cer")

        # opens the ssl key file for writing (in binary mode) and
        # then writes the current data into it so that it may be
        # used by the encryption infra-structure
        key_file = open(key_path, "wb")
        try: key_file.write(key_data)
        finally: key_file.close()

        # opens the temporary certificate file and writes
        # the retrieved certificate data into it, to be used
        # temporarily by the ssl infra-structure
        cer_file = open(cer_path, "wb")
        try: cer_file.write(cer_data)
        finally: cer_file.close()

        # retrieves the app key for the retrieved app by unpacking the current
        # app structure into the appropriate values
        app_key = app.key

        # saves the original event name for the received event, so that it may
        # be used latter for debugging/log purposes
        root_event = event

        # resolves the complete set of (extra) channels for the provided
        # event assuming that it may be associated with alias, then creates
        # the complete list of event containing also the "extra" events
        extra = self.owner.get_channels(app_key, event)
        events = [event] + extra

        # retrieves the complete set of subscriptions for the current APN
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
        count = len(tokens)

        # prints a logging message about the various (web) subscriptions
        # that were found for the event that was triggered
        self.logger.debug("Found %d APN subscription(s) for '%s'" % (count, root_event))

        # creates the counter that will be used by the cleanup function
        # to know exactly when to remove the ssl associated files
        pending = len(tokens)
        clojure = dict(pending = pending)

        # creates the cleanup function that will be called for
        # the close operation of the APN client, this function
        # will remove the temporary path when called as a response
        # to the "stop" of the last client
        def cleanup(client):
            pending = clojure["pending"]
            pending -= 1
            clojure["pending"] = pending
            if not pending == 0: return
            shutil.rmtree(path, ignore_errors = True)

        # iterates over the complete set of tokens to be notified and notifies
        # them using the current APN client infra-structure
        for token in tokens:
            # in case the current token is present in the current
            # map of invalid items must skip iteration as the message
            # has probably already been sent "to the token"
            if token in invalid: continue

            # prints a debug message about the APN message that
            # is going to be sent (includes token)
            self.logger.debug("Sending APN message to '%s'" % token)

            # creates the new APN client to be used and uses it to
            # send the new message (should be correctly serialized)
            apn_client = netius.clients.APNClient()
            apn_client.bind("stop", cleanup)
            apn_client.message(
                token,
                message = message,
                sandbox = sandbox,
                key_file = key_path,
                cer_file = cer_path
            )

            # adds the current token to the list of invalid item for
            # the current message sending stream
            invalid[token] = True

    def load(self):
        subs = pushi.APN.find()
        for sub in subs:
            app_id = sub.app_id
            token = sub.token
            event = sub.event
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

    def subscriptions(self, token = None, event = None):
        filter = dict()
        if token: filter["token"] = token
        if event: filter["event"] = event
        subscriptions = pushi.APN.find(map = True, **filter)
        return dict(
            subscriptions = subscriptions
        )

    def subscribe(self, apn, auth = None, unsubscribe = True):
        self.logger.debug("Subscribing '%s' for '%s'" % (apn.token, apn.event))

        is_private = apn.event.startswith("private-") or\
            apn.event.startswith("presence-") or apn.event.startswith("peer-") or\
            apn.event.startswith("personal-")

        is_private and self.owner.verify(apn.app_key, apn.token, apn.event, auth)
        unsubscribe and self.unsubscribe(apn.token, force = False)

        exists = pushi.APN.exists(
            token = apn.token,
            event = apn.event
        )
        if exists: apn = exists
        else: apn.save()

        self.logger.debug("Subscribed '%s' for '%s'" % (apn.token, apn.event))

        return apn

    def unsubscribe(self, token, event = None, force = True):
        self.logger.debug("Unsubscribing '%s' from '%s'" % (token, event or "*"))

        kwargs = dict(token = token, raise_e = force)
        if event: kwargs["event"] = event

        apn = pushi.APN.get(**kwargs)
        if not apn: return None

        apn.delete()

        self.logger.debug("Unsubscribed '%s' for '%s'" % (token, event or "*"))

        return apn

    def unsubscribes(self, token, event = None):
        kwargs = dict(token = token)
        if event: kwargs["event"] = event

        apns = pushi.APN.find(**kwargs)
        for apn in apns: apn.delete()

        return apns
