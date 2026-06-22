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

from pushi.base import web


class WebHandlerTest(unittest.TestCase):
    """
    Unit tests for the WebHandler class.

    Tests the Web (Hook) handler functionality including subscription
    resolution and direct URL sending with configurable HTTP methods.
    """

    def setUp(self):
        """
        Sets up test fixtures before each test method.
        """

        # creates a mock owner with required attributes
        self.mock_owner = mock.MagicMock()
        self.mock_owner.app = mock.MagicMock()
        self.mock_owner.app.logger = mock.MagicMock()

        # creates the handler instance
        self.handler = web.WebHandler(self.mock_owner)

    def test_init(self):
        """
        Tests that the handler initializes correctly with proper attributes.
        """

        self.assertEqual(self.handler.name, "web")
        self.assertEqual(self.handler.owner, self.mock_owner)
        self.assertIsInstance(self.handler.subs, dict)
        self.assertEqual(len(self.handler.subs), 0)

    def test_send_resolves_urls(self):
        """
        Tests send method resolves subscriptions and delegates to send_to_urls.
        """

        # mocks the app and the resolved channels for the event
        mock_app = mock.MagicMock()
        mock_app.key = "appkey123"
        self.mock_owner.get_app.return_value = mock_app
        self.mock_owner.get_channels.return_value = []

        # registers a URL for the event and replaces the direct send method
        self.handler.subs = {"app123": {"notifications": ["https://example.com/hook"]}}
        self.handler.send_to_urls = mock.MagicMock()

        self.handler.send("app123", "notifications", {"data": "test"})

        # verifies the resolved URLs were delegated to send_to_urls
        call_args = self.handler.send_to_urls.call_args
        self.assertEqual(call_args[0][0], set(["https://example.com/hook"]))

    def test_send_to_urls_empty(self):
        """
        Tests send_to_urls returns success with no URLs to notify.
        """

        result = self.handler.send_to_urls([], {"event": "ping"})

        self.assertEqual(result["success"], True)
        self.assertEqual(result["urls"], [])

    def test_send_to_urls_post(self):
        """
        Tests send_to_urls dispatches a POST request to the target URL.
        """

        # patches the HTTP client so that no real connection is made
        with mock.patch("netius.clients.HTTPClient") as mock_client:
            mock_loop = mock.MagicMock()
            mock_protocol = mock.MagicMock()
            mock_client.post_s.return_value = (mock_loop, mock_protocol)

            result = self.handler.send_to_urls(
                "https://example.com/hook", {"event": "ping"}, invalid={}
            )

            # verifies the POST request was dispatched and the URL collected
            self.assertEqual(result["success"], True)
            self.assertEqual(result["urls"], ["https://example.com/hook"])
            self.assertEqual(result["method"], "POST")
            mock_client.post_s.assert_called_once()

    def test_send_to_urls_get(self):
        """
        Tests send_to_urls dispatches a GET request when requested.
        """

        # patches the HTTP client so that no real connection is made
        with mock.patch("netius.clients.HTTPClient") as mock_client:
            mock_loop = mock.MagicMock()
            mock_protocol = mock.MagicMock()
            mock_client.get_s.return_value = (mock_loop, mock_protocol)

            result = self.handler.send_to_urls(
                "https://example.com/hook",
                {"event": "ping"},
                method="GET",
                invalid={},
            )

            # verifies the GET request was dispatched and the URL collected
            self.assertEqual(result["success"], True)
            self.assertEqual(result["urls"], ["https://example.com/hook"])
            mock_client.get_s.assert_called_once()

    def test_send_to_urls_unknown_method(self):
        """
        Tests send_to_urls skips URLs with an unsupported HTTP method.
        """

        result = self.handler.send_to_urls(
            "https://example.com/hook", {"event": "ping"}, method="PATCH", invalid={}
        )

        # verifies no URL was sent as the method is not supported
        self.assertEqual(result["success"], True)
        self.assertEqual(result["urls"], [])

    def test_send_to_urls_custom_headers(self):
        """
        Tests send_to_urls merges custom headers with the default ones.
        """

        # patches the HTTP client so that no real connection is made
        with mock.patch("netius.clients.HTTPClient") as mock_client:
            mock_loop = mock.MagicMock()
            mock_protocol = mock.MagicMock()
            mock_client.post_s.return_value = (mock_loop, mock_protocol)

            self.handler.send_to_urls(
                "https://example.com/hook",
                {"event": "ping"},
                headers={"x-token": "secret"},
                invalid={},
            )

            # verifies the custom header was merged with the content type
            call_args = mock_client.post_s.call_args
            request_headers = call_args[1]["headers"]
            self.assertEqual(request_headers["x-token"], "secret")
            self.assertEqual(request_headers["content-type"], "application/json")


if __name__ == "__main__":
    unittest.main()
