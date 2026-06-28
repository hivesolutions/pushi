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

import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from pushi.app.controllers import web_push


class WebPushControllerTest(unittest.TestCase):
    """
    Unit tests for the WebPushController class.

    Tests the Web Push REST API endpoints functionality, with a special
    focus on the (correct) handling of the authentication values that are
    provided both in the query parameters and in the JSON body.
    """

    def setUp(self):
        """
        Sets up test fixtures before each test method.
        """

        # creates a mock owner (app) with required attributes
        self.mock_owner = mock.MagicMock()

        # creates the controller instance
        self.controller = web_push.WebPushController(owner=self.mock_owner)

    def test_create_uses_body_auth_secret(self):
        """
        Tests that the subscription stores the (browser) authentication secret
        from the JSON body and not the (channel) authentication token from the
        query parameters, as both share the "auth" name.
        """

        # the (browser) authentication secret comes in the JSON body while the
        # (channel) authentication token comes in the query parameters
        body = dict(
            endpoint="https://fcm.googleapis.com/fcm/send/endpoint123",
            p256dh="browser_p256dh_key",
            auth="browser_auth_secret",
            event="personal-username",
        )
        channel_token = "app_key:channel_auth_token"

        # mocks the request so that the JSON body is returned by get_json and
        # the query "auth" value is returned by the field retrieval
        self.controller.request = mock.MagicMock()
        self.controller.request.get_json.return_value = body
        self.controller.field = mock.MagicMock(
            side_effect=lambda name, *args, **kwargs: (
                channel_token if name == "auth" else False
            )
        )

        # makes the subscribe operation return the same Web Push model it
        # receives so that its attributes may be inspected afterwards
        handler = self.mock_owner.state.web_push_handler
        handler.subscribe.side_effect = lambda web_push, **kwargs: web_push

        self.controller.create()

        # verifies the subscribe operation received the channel authentication
        # token and that the stored secret is the (browser) one from the body
        _args, kwargs = handler.subscribe.call_args
        web_push_model = handler.subscribe.call_args[0][0]
        self.assertEqual(kwargs["auth"], channel_token)
        self.assertEqual(web_push_model.auth, "browser_auth_secret")
        self.assertNotEqual(web_push_model.auth, channel_token)


if __name__ == "__main__":
    unittest.main()
