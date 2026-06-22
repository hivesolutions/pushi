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

from pushi.base import apn


class APNHandlerTest(unittest.TestCase):
    """
    Unit tests for the APNHandler class.

    Tests the Apple Push Notification handler functionality including
    subscription resolution and direct token sending.
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
        self.handler = apn.APNHandler(self.mock_owner)

    def test_init(self):
        """
        Tests that the handler initializes correctly with proper attributes.
        """

        self.assertEqual(self.handler.name, "apn")
        self.assertEqual(self.handler.owner, self.mock_owner)
        self.assertIsInstance(self.handler.subs, dict)
        self.assertEqual(len(self.handler.subs), 0)

    def test_send_without_message(self):
        """
        Tests send method raises when no message is defined.
        """

        self.assertRaises(
            RuntimeError, self.handler.send, "app123", "notifications", {}
        )

    def test_send_resolves_tokens(self):
        """
        Tests send method resolves subscriptions and delegates to send_to_tokens.
        """

        # mocks the app and the resolved channels for the event
        mock_app = mock.MagicMock()
        mock_app.key = "appkey123"
        self.mock_owner.get_app.return_value = mock_app
        self.mock_owner.get_channels.return_value = []

        # registers a token for the event and replaces the direct send method
        self.handler.subs = {"app123": {"notifications": ["token123"]}}
        self.handler.send_to_tokens = mock.MagicMock()

        self.handler.send("app123", "notifications", {"data": "test"})

        # verifies the resolved tokens were delegated to send_to_tokens
        call_args = self.handler.send_to_tokens.call_args
        self.assertEqual(call_args[0][0], set(["token123"]))
        self.assertEqual(call_args[1]["app"], mock_app)

    def test_send_to_tokens_without_message(self):
        """
        Tests send_to_tokens raises when no message is defined.
        """

        self.assertRaises(
            RuntimeError,
            self.handler.send_to_tokens,
            ["token123"],
            None,
            key_data="key",
            cer_data="cer",
        )

    def test_send_to_tokens_without_credentials(self):
        """
        Tests send_to_tokens raises when no APN credentials are defined.
        """

        self.assertRaises(
            RuntimeError,
            self.handler.send_to_tokens,
            ["token123"],
            {"alert": "Hello"},
        )

    def test_send_to_tokens_empty(self):
        """
        Tests send_to_tokens returns success with no tokens to notify.
        """

        result = self.handler.send_to_tokens(
            [], {"alert": "Hello"}, key_data="key", cer_data="cer"
        )

        self.assertEqual(result["success"], True)
        self.assertEqual(result["tokens"], [])

    def test_send_to_tokens_credentials_from_app(self):
        """
        Tests send_to_tokens resolves credentials from the provided app.
        """

        # mocks an app without credentials so the empty tokens path
        # is reached after the credentials have been resolved
        mock_app = mock.MagicMock()
        mock_app.apn_key = "key"
        mock_app.apn_cer = "cer"
        mock_app.apn_sandbox = True

        result = self.handler.send_to_tokens([], {"alert": "Hello"}, app=mock_app)

        self.assertEqual(result["success"], True)
        self.assertEqual(result["tokens"], [])


if __name__ == "__main__":
    unittest.main()
