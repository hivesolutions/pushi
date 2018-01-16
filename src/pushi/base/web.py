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

import json

import netius.clients

import pushi

from . import handler

class WebHandler(handler.Handler):
    """
    Event handler to be used for web based "hooks".
    This handler provides the abstraction for the http
    client based callbacks.
    """

    def __init__(self, owner):
        handler.Handler.__init__(self, owner, name = "web")
        self.subs = {}

    def send(self, app_id, event, json_d, invalid = {}):
        # retrieves the reference to the app structure associated with the
        # id for which the message is being send
        app = self.owner.get_app(app_id = app_id)

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

        # retrieves the complete set of subscriptions for the current web
        # infra-structure to be able to resolve the appropriate urls
        subs = self.subs.get(app_id, {})

        # creates the initial list of urls to be notified and then populates
        # the list with the various url associated with the complete set of
        # resolved events, note that a set is created at the end so that one
        # url gets notified only once (no double notifications)
        urls = []
        for event in events:
            _urls = subs.get(event, [])
            urls.extend(_urls)
        urls = set(urls)
        count = len(urls)

        # prints a logging message about the various (web) subscriptions
        # that were found for the event that was triggered
        self.logger.debug("Found %d web subscription(s) for '%s'" % (count, root_event))

        # serializes the json message so that it's possible to send it using
        # the http client to the endpoints and then creates the map of headers
        # that is going to be used in the post messages to be sent
        data = json.dumps(json_d)
        headers = {
            "content-type" : "application/json"
        }

        # creates the on message function that is going to be used at the end of
        # the request to be able to close the client, this is a clojure and so
        # current local variables will be exposed to the method
        def on_message(client, parser, message):
            client.close()

        # creates the on close function that will be responsible for the closing
        # of the client as defined by the web implementation
        def on_close(client, connection):
            client.close()

        # iterates over the complete set of urls that are going to
        # be notified about the message, each of them is going to
        # received an http post request with the data
        for url in urls:
            # in case the current token is present in the current
            # map of invalid items must skip iteration as the message
            # has probably already been sent "to the target url"
            if url in invalid: continue

            # prints a debug message about the web message that
            # is going to be sent (includes url)
            self.logger.debug("Sending post request to '%s'" % url)

            # creates the http client to be used in the post request and
            # sets the headers and the data then registers for the message
            # event so that the client may be closed
            http_client = netius.clients.HTTPClient()
            http_client.post(url, headers = headers, data = data)
            http_client.bind("message", on_message)
            http_client.bind("close", on_close)

            # adds the current url to the list of invalid item for
            # the current message sending stream
            invalid[url] = True

    def load(self):
        subs = pushi.Web.find()
        for sub in subs:
            app_id = sub.app_id
            url = sub.url
            event = sub.event
            self.add(app_id, url, event)

    def add(self, app_id, url, event):
        events = self.subs.get(app_id, {})
        urls = events.get(event, [])
        urls.append(url)
        events[event] = urls
        self.subs[app_id] = events

    def remove(self, app_id, url, event):
        events = self.subs.get(app_id, {})
        urls = events.get(event, [])
        if url in urls: urls.remove(url)

    def subscriptions(self, url = None, event = None):
        filter = dict()
        if url: filter["url"] = url
        if event: filter["event"] = event
        subscriptions = pushi.Web.find(map = True, **filter)
        return dict(
            subscriptions = subscriptions
        )

    def subscribe(self, web, auth = None, unsubscribe = True):
        self.logger.debug("Subscribing '%s' for '%s'" % (web.url, web.event))

        is_private = web.event.startswith("private-") or\
            web.event.startswith("presence-") or web.event.startswith("peer-") or\
            web.event.startswith("personal-")

        is_private and self.owner.verify(web.app_key, web.url, web.event, auth)
        unsubscribe and self.unsubscribe(web.url, force = False)

        exists = pushi.Web.exists(
            url = web.url,
            event = web.event
        )
        if exists: web = exists
        else: web.save()

        self.logger.debug("Subscribed '%s' for '%s'" % (web.url, web.event))

        return web

    def unsubscribe(self, url, event = None, force = True):
        self.logger.debug("Unsubscribing '%s' from '%s'" % (url, event or "*"))

        kwargs = dict(url = url, raise_e = force)
        if event: kwargs["event"] = event

        web = pushi.Web.get(**kwargs)
        if not web: return None

        web.delete()

        self.logger.debug("Unsubscribed '%s' for '%s'" % (url, event or "*"))

        return web

    def unsubscribes(self, url, event = None):
        kwargs = dict(token = url)
        if event: kwargs["event"] = event

        webs = pushi.Web.find(**kwargs)
        for web in webs: web.delete()

        return webs
