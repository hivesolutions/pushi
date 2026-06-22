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

from pushi.base import smtp


class SMTPHandlerTest(unittest.TestCase):
    """
    Unit tests for the SMTPHandler class.

    Tests the SMTP email handler functionality including subscription
    resolution, configuration resolution and direct email sending.
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
        self.handler = smtp.SMTPHandler(self.mock_owner)

    def test_init(self):
        """
        Tests that the handler initializes correctly with proper attributes.
        """

        self.assertEqual(self.handler.name, "smtp")
        self.assertEqual(self.handler.owner, self.mock_owner)
        self.assertIsInstance(self.handler.subs, dict)
        self.assertEqual(len(self.handler.subs), 0)

    def test_send_resolves_emails(self):
        """
        Tests send method resolves subscriptions and delegates to send_to_emails.
        """

        # mocks the app and the resolved channels for the event
        mock_app = mock.MagicMock()
        mock_app.key = "appkey123"
        self.mock_owner.get_app.return_value = mock_app
        self.mock_owner.get_channels.return_value = []

        # registers an email for the event and replaces the direct send method
        self.handler.subs = {"app123": {"notifications": ["user@example.com"]}}
        self.handler.send_to_emails = mock.MagicMock()

        self.handler.send("app123", "notifications", {"data": "test"})

        # verifies the resolved emails were delegated to send_to_emails
        call_args = self.handler.send_to_emails.call_args
        self.assertEqual(call_args[0][0], set(["user@example.com"]))
        self.assertEqual(call_args[1]["app"], mock_app)

    def test_send_to_emails_without_host(self):
        """
        Tests send_to_emails returns an error when no SMTP host is configured.
        """

        # mocks the configuration resolution to return no host
        self.handler._resolve_smtp_config = mock.MagicMock(return_value={})

        result = self.handler.send_to_emails("user@example.com", "Hello", "World")

        # verifies the error result and the logged warning
        self.assertEqual(result["success"], False)
        self.assertEqual(result["error"], "SMTP host not configured")
        self.mock_owner.app.logger.warning.assert_called()

    def test_send_to_emails_without_sender(self):
        """
        Tests send_to_emails returns an error when no SMTP sender is configured.
        """

        # mocks the configuration resolution to return a host but no sender
        self.handler._resolve_smtp_config = mock.MagicMock(
            return_value={"host": "smtp.example.com"}
        )

        result = self.handler.send_to_emails("user@example.com", "Hello", "World")

        # verifies the error result and the logged warning
        self.assertEqual(result["success"], False)
        self.assertEqual(result["error"], "SMTP sender not configured")
        self.mock_owner.app.logger.warning.assert_called()

    def test_send_to_emails_empty(self):
        """
        Tests send_to_emails returns success with no recipients to notify.
        """

        # mocks the configuration resolution with a valid host and sender
        self.handler._resolve_smtp_config = mock.MagicMock(
            return_value={"host": "smtp.example.com", "sender": "from@example.com"}
        )

        result = self.handler.send_to_emails([], "Hello", "World")

        self.assertEqual(result["success"], True)
        self.assertEqual(result["recipients"], [])

    def test_send_to_emails_success(self):
        """
        Tests successful send of an email through the SMTP client.
        """

        # mocks the configuration resolution with a valid host and sender
        self.handler._resolve_smtp_config = mock.MagicMock(
            return_value={"host": "smtp.example.com", "sender": "from@example.com"}
        )

        # patches the SMTP client so that no real connection is made
        with mock.patch("netius.clients.SMTPClient") as mock_client:
            result = self.handler.send_to_emails(
                "user@example.com", "Hello", "World", invalid={}
            )

            # verifies the recipient was sent and the client was used
            self.assertEqual(result["success"], True)
            self.assertEqual(result["recipients"], ["user@example.com"])
            mock_client.return_value.message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
