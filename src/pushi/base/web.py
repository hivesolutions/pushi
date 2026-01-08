#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (c) 2008-2024 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import json

import netius.clients

import pushi

from . import handler


class WebHandler(handler.Handler):
    """
    Event handler to be used for Web based "hooks".

    This handler provides the abstraction for the HTTP
    client based callbacks.

    Notification here will be sent using a HTTP POST
    request to the URL specified in the subscription.

    :see: https://en.wikipedia.org/wiki/Webhook
    """

    def __init__(self, owner):
        handler.Handler.__init__(self, owner, name="web")
        self.subs = {}

    def send(self, app_id, event, json_d, invalid={}):
        # retrieves the reference to the app structure associated with the
        # id for which the message is being send
        app = self.owner.get_app(app_id=app_id)

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

        # creates the initial list of URLs to be notified and then populates
        # the list with the various URL associated with the complete set of
        # resolved events, note that a set is created at the end so that one
        # URL gets notified only once (no double notifications)
        urls = []
        for event in events:
            _urls = subs.get(event, [])
            urls.extend(_urls)
        urls = set(urls)
        count = len(urls)

        # prints a logging message about the various (Web) subscriptions
        # that were found for the event that was triggered
        self.logger.debug(
            "Found %d Web (Hook) subscription(s) for '%s'" % (count, root_event)
        )

        # serializes the JSON message so that it's possible to send it using
        # the HTTP client to the endpoints and then creates the map of headers
        # that is going to be used in the post messages to be sent
        data = json.dumps(json_d)
        headers = {"content-type": "application/json"}

        # creates the on message function that is going to be used at the end of
        # the request to be able to close the protocol, this is a clojure and so
        # current local variables will be exposed to the method
        def on_message(protocol, parser, message):
            protocol.close()

        # creates the on close function that will be responsible for the stopping
        # of the loop as defined by the Web (Hook) implementation
        def on_finish(protocol):
            netius.compat_loop(loop).stop()

        # iterates over the complete set of URLs that are going to
        # be notified about the message, each of them is going to
        # received an HTTP post request with the data
        for url in urls:
            # in case the current token is present in the current
            # map of invalid items must skip iteration as the message
            # has probably already been sent "to the target URL"
            if url in invalid:
                continue

            # prints a debug message about the Web (Hook) message that
            # is going to be sent (includes URL)
            self.logger.debug("Sending POST request to '%s'" % url)

            # creates the HTTP protocol to be used in the POST request and
            # sets the headers and the data then registers for the message
            # event so that the loop and protocol may be closed
            loop, protocol = netius.clients.HTTPClient.post_s(
                url, headers=headers, data=data
            )
            protocol.bind("message", on_message)
            protocol.bind("finish", on_finish)
            loop.run_forever()

            # adds the current URL to the list of invalid items for
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
        if url in urls:
            urls.remove(url)

    def subscriptions(self, url=None, event=None):
        filter = dict()
        if url:
            filter["url"] = url
        if event:
            filter["event"] = event
        subscriptions = pushi.Web.find(map=True, **filter)
        return dict(subscriptions=subscriptions)

    def subscribe(self, web, auth=None, unsubscribe=True):
        self.logger.debug("Subscribing '%s' for '%s'" % (web.url, web.event))

        is_private = (
            web.event.startswith("private-")
            or web.event.startswith("presence-")
            or web.event.startswith("peer-")
            or web.event.startswith("personal-")
        )

        if is_private:
            self.owner.verify(web.app_key, web.url, web.event, auth)
        if unsubscribe:
            self.unsubscribe(web.url, force=False)

        exists = pushi.Web.exists(url=web.url, event=web.event)
        if exists:
            web = exists
        else:
            web.save()

        self.logger.debug("Subscribed '%s' for '%s'" % (web.url, web.event))

        return web

    def unsubscribe(self, url, event=None, force=True):
        self.logger.debug("Unsubscribing '%s' from '%s'" % (url, event or "*"))

        kwargs = dict(url=url, raise_e=force)
        if event:
            kwargs["event"] = event

        web = pushi.Web.get(**kwargs)
        if not web:
            return None

        web.delete()

        self.logger.debug("Unsubscribed '%s' for '%s'" % (url, event or "*"))

        return web

    def unsubscribes(self, url, event=None):
        kwargs = dict(token=url)
        if event:
            kwargs["event"] = event

        webs = pushi.Web.find(**kwargs)
        for web in webs:
            web.delete()

        return webs
