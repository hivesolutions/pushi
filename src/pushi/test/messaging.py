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
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from pushi.base import messaging


class MessengerTest(unittest.TestCase):
    """
    Unit tests for the Messenger class.

    Tests the direct messaging API functionality including adapter
    dispatching and delegation to the underlying handler implementations.
    """

    def setUp(self):
        """
        Sets up test fixtures before each test method.
        """

        # creates a mock app and the messenger instance under test
        self.mock_app = mock.MagicMock()
        self.messenger = messaging.Messenger(app=self.mock_app)

        # replaces the underlying handlers with mocks so that the
        # delegation may be asserted without performing real sending
        self.messenger._apn_handler = mock.MagicMock()
        self.messenger._smtp_handler = mock.MagicMock()
        self.messenger._web_handler = mock.MagicMock()
        self.messenger._web_push_handler = mock.MagicMock()

    def test_init(self):
        """
        Tests that the messenger initializes correctly with proper attributes.
        """

        messenger = messaging.Messenger()

        self.assertEqual(messenger.app, None)
        self.assertIsInstance(messenger.logger, messaging._NullLogger)
        self.assertIsInstance(messenger._apn_handler, messaging._StandaloneAPNHandler)
        self.assertIsInstance(messenger._smtp_handler, messaging._StandaloneSMTPHandler)
        self.assertIsInstance(messenger._web_handler, messaging._StandaloneWebHandler)
        self.assertIsInstance(
            messenger._web_push_handler, messaging._StandaloneWebPushHandler
        )

    def test_send_single_adapter(self):
        """
        Tests sending through a single adapter passed as a string.
        """

        self.messenger._apn_handler.send_to_tokens.return_value = dict(
            success=True, tokens=["token123"]
        )

        results = self.messenger.send(
            "apn", data={"alert": "Hello"}, apn_tokens=["token123"]
        )

        # verifies the adapter was dispatched and its result collected
        self.assertIn("apn", results)
        self.assertEqual(results["apn"]["success"], True)
        self.messenger._apn_handler.send_to_tokens.assert_called_once()

    def test_send_multiple_adapters(self):
        """
        Tests sending through multiple adapters in a single call.
        """

        self.messenger._apn_handler.send_to_tokens.return_value = dict(success=True)
        self.messenger._smtp_handler.send_to_emails.return_value = dict(success=True)

        results = self.messenger.send(
            ["apn", "email"],
            data={"title": "Hello"},
            apn_tokens=["token123"],
            email_to="user@example.com",
        )

        # verifies both adapters were dispatched and collected
        self.assertIn("apn", results)
        self.assertIn("email", results)
        self.messenger._apn_handler.send_to_tokens.assert_called_once()
        self.messenger._smtp_handler.send_to_emails.assert_called_once()

    def test_send_unknown_adapter(self):
        """
        Tests sending through an unknown adapter returns an error result.
        """

        results = self.messenger.send("invalid", data={"title": "Hello"})

        # verifies the unknown adapter is reported as a failure
        self.assertEqual(results["invalid"]["success"], False)
        self.assertIn("Unknown adapter", results["invalid"]["error"])

    def test_send_adapter_exception(self):
        """
        Tests that an exception in an adapter is captured as a failure.
        """

        self.messenger._apn_handler.send_to_tokens.side_effect = RuntimeError("boom")

        results = self.messenger.send("apn", apn_tokens=["token123"])

        # verifies the exception is captured in the result dictionary
        self.assertEqual(results["apn"]["success"], False)
        self.assertEqual(results["apn"]["error"], "boom")

    def test_send_adapter_alias(self):
        """
        Tests that an adapter alias is dispatched under its canonical key.
        """

        self.messenger._smtp_handler.send_to_emails.return_value = dict(success=True)

        results = self.messenger.send("smtp", email_to="user@example.com")

        # verifies the "smtp" alias is reported under the "email" key
        self.assertIn("email", results)
        self.assertNotIn("smtp", results)
        self.messenger._smtp_handler.send_to_emails.assert_called_once()

    def test_send_adapter_exception_alias(self):
        """
        Tests that an alias failure is keyed by its canonical name.
        """

        self.messenger._web_handler.send_to_urls.side_effect = RuntimeError("boom")

        results = self.messenger.send("web", webhook_urls=["https://example.com/hook"])

        # verifies the "web" alias failure is reported under the "webhook" key
        self.assertEqual(results["webhook"]["success"], False)
        self.assertEqual(results["webhook"]["error"], "boom")

    def test_send_email_body_from_data(self):
        """
        Tests that the email body defaults to the JSON dump of the data.
        """

        self.messenger._smtp_handler.send_to_emails.return_value = dict(success=True)

        data = {"title": "Hello", "body": "World"}
        self.messenger.send("email", data=data, email_to="user@example.com")

        # verifies the body was serialized from the data payload
        call_args = self.messenger._smtp_handler.send_to_emails.call_args
        self.assertEqual(call_args[1]["body"], json.dumps(data, indent=2))

    def test_send_apn(self):
        """
        Tests that send_apn delegates to the APN handler with the app.
        """

        self.messenger._apn_handler.send_to_tokens.return_value = dict(success=True)

        self.messenger.send_apn(tokens=["token123"], message={"alert": "Hello"})

        # verifies the delegation includes the app and the provided values
        call_args = self.messenger._apn_handler.send_to_tokens.call_args
        self.assertEqual(call_args[1]["tokens"], ["token123"])
        self.assertEqual(call_args[1]["message"], {"alert": "Hello"})
        self.assertEqual(call_args[1]["app"], self.mock_app)

    def test_send_email(self):
        """
        Tests that send_email delegates to the SMTP handler with the app.
        """

        self.messenger._smtp_handler.send_to_emails.return_value = dict(success=True)

        self.messenger.send_email(to="user@example.com", subject="Hello", body="World")

        # verifies the delegation maps the recipient and content values
        call_args = self.messenger._smtp_handler.send_to_emails.call_args
        self.assertEqual(call_args[1]["emails"], "user@example.com")
        self.assertEqual(call_args[1]["subject"], "Hello")
        self.assertEqual(call_args[1]["body"], "World")
        self.assertEqual(call_args[1]["app"], self.mock_app)

    def test_send_webhook(self):
        """
        Tests that send_webhook delegates to the Web handler.
        """

        self.messenger._web_handler.send_to_urls.return_value = dict(success=True)

        self.messenger.send_webhook(
            urls=["https://example.com/hook"], data={"event": "ping"}
        )

        # verifies the delegation maps the URLs and the data values
        call_args = self.messenger._web_handler.send_to_urls.call_args
        self.assertEqual(call_args[1]["urls"], ["https://example.com/hook"])
        self.assertEqual(call_args[1]["data"], {"event": "ping"})

    def test_send_web_push(self):
        """
        Tests that send_web_push delegates to the Web Push handler with the app.
        """

        self.messenger._web_push_handler.send_to_subscriptions.return_value = dict(
            success=True
        )

        subscriptions = [{"endpoint": "https://...", "p256dh": "key", "auth": "secret"}]
        self.messenger.send_web_push(
            subscriptions=subscriptions, message={"title": "Hello"}
        )

        # verifies the delegation maps the subscriptions and the app values
        call_args = self.messenger._web_push_handler.send_to_subscriptions.call_args
        self.assertEqual(call_args[1]["subscriptions"], subscriptions)
        self.assertEqual(call_args[1]["message"], {"title": "Hello"})
        self.assertEqual(call_args[1]["app"], self.mock_app)


if __name__ == "__main__":
    unittest.main()
