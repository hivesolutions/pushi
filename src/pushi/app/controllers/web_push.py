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

import appier

import pushi


class WebPushController(appier.Controller):
    """
    Controller for Web Push API endpoints.

    Provides REST API for managing Web Push subscriptions,
    including subscribe and unsubscribe operations.
    """

    @appier.private
    @appier.route("/web_pushes", "GET", opts=dict(cors=True))
    def list(self):
        """
        Lists Web Push subscriptions with optional filtering.

        Query parameters:
        - app_key: The application key (required)
        - endpoint: Filter by endpoint URL
        - event: Filter by event/channel name

        :rtype: Dictionary
        :return: Dictionary containing list of subscriptions.
        """

        # retrieves the app key from request and looks up the app
        # to filter subscriptions by instance
        app_key = self.field("app_key", mandatory=True)
        app = pushi.App.get(key=app_key)

        endpoint = self.field("endpoint", None)
        event = self.field("event", None)
        return self.state.web_push_handler.subscriptions(
            endpoint=endpoint, event=event, instance=app.ident
        )

    @appier.route("/web_pushes", "POST", opts=dict(cors=True))
    def create(self):
        """
        Creates a new Web Push subscription.

        Form/JSON parameters:
        - endpoint: The push service endpoint URL (required)
        - p256dh: The P256DH encryption key (required)
        - auth: The authentication secret (required)
        - event: The event/channel name (required)
        - auth: Optional authentication token for private channels
        - unsubscribe: Whether to remove existing subscriptions (default: false)

        :rtype: Dictionary
        :return: The created subscription object.
        """

        # retrieves the app key from request and looks up the app
        # to set the proper instance/app_id context for the subscription
        app_key = self.field("app_key", mandatory=True)
        app = pushi.App.get(key=app_key)

        auth = self.field("auth", None)
        unsubscribe = self.field("unsubscribe", False, cast=bool)
        web_push = pushi.WebPush.new()
        web_push.instance = app.ident
        web_push = self.state.web_push_handler.subscribe(
            web_push, auth=auth, unsubscribe=unsubscribe
        )
        return web_push.map()

    @appier.route(r"/web_pushes/<regex('.+'):endpoint>", "DELETE", opts=dict(cors=True))
    def delete(self, endpoint):
        """
        Deletes Web Push subscriptions for a given endpoint.

        If event is provided, deletes only the subscription for that
        specific event. Otherwise, deletes all subscriptions for the endpoint.

        Query parameters:
        - app_key: The application key (required)
        - event: The event/channel name (optional)
        - force: Whether to raise error if not found (default: false)

        :type endpoint: String
        :param endpoint: The push endpoint URL (path parameter, URL-encoded).
        :rtype: Dictionary
        :return: Dictionary containing deleted subscription(s).
        """

        # retrieves the app key from request and looks up the app
        # to filter subscriptions by instance
        app_key = self.field("app_key", mandatory=True)
        app = pushi.App.get(key=app_key)

        event = self.field("event", None)
        force = self.field("force", False, cast=bool)

        # if event is provided, deletes only the specific subscription
        # otherwise deletes all subscriptions for the endpoint
        if event:
            web_push = self.state.web_push_handler.unsubscribe(
                endpoint, event=event, instance=app.ident, force=force
            )
            return web_push.map() if web_push else dict()
        else:
            web_pushes = self.state.web_push_handler.unsubscribes(
                endpoint, instance=app.ident
            )
            return dict(subscriptions=[web_push.map() for web_push in web_pushes])
