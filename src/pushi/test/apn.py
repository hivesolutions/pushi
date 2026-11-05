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

import os
import json
import base64
import binascii
import unittest

try:
    from unittest import mock
except ImportError:
    import mock

from pushi.base import apn

try:
    import cryptography.hazmat.primitives.hashes
    import cryptography.hazmat.primitives.serialization
    import cryptography.hazmat.primitives.asymmetric.ec
    import cryptography.hazmat.primitives.asymmetric.utils
except ImportError:
    cryptography = None


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
        self.assertIsInstance(self.handler.provider_tokens, dict)
        self.assertEqual(len(self.handler.provider_tokens), 0)

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

    def test_send_to_tokens_without_certificate(self):
        """
        Tests send_to_tokens raises when only the key of the certificate
        based authentication is defined.
        """

        self.assertRaises(
            RuntimeError,
            self.handler.send_to_tokens,
            ["token123"],
            {"alert": "Hello"},
            key_data="key",
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

    def test_send_to_tokens_default_invalid(self):
        """
        Tests send_to_tokens notifies the same token again in a second
        direct send, not sharing the map of invalid items between calls.
        """

        self.handler.send_h2 = mock.MagicMock(
            side_effect=lambda tokens, message, **kwargs: kwargs["invalid"].update(
                dict((token, True) for token in tokens)
            )
            or dict(success=True, tokens=list(tokens))
        )

        with mock.patch.object(apn, "httpx", mock.MagicMock()):
            first = self.handler.send_to_tokens(
                ["token123"], "Hello", key_data="key", cer_data="cer"
            )
            second = self.handler.send_to_tokens(
                ["token123"], "Hello", key_data="key", cer_data="cer"
            )

        first_invalid = self.handler.send_h2.call_args_list[0][1]["invalid"]
        second_invalid = self.handler.send_h2.call_args_list[1][1]["invalid"]
        self.assertEqual(first["tokens"], ["token123"])
        self.assertEqual(second["tokens"], ["token123"])
        self.assertIsNot(first_invalid, second_invalid)

    def test_send_to_tokens_token_from_app(self):
        """
        Tests send_to_tokens uses the token based authentication with the
        credentials of the provided app, sending through the HTTP/2 API.
        """

        # mocks an app with the token based credentials only
        mock_app = mock.MagicMock()
        mock_app.apn_key = None
        mock_app.apn_cer = None
        mock_app.apn_auth_key = "auth_key"
        mock_app.apn_key_id = "KEY123"
        mock_app.apn_team_id = "TEAM123"
        mock_app.apn_topic = "pt.hive.app"
        mock_app.apn_sandbox = True

        # replaces both the HTTP/2 send and the provider token generation
        self.handler.send_h2 = mock.MagicMock(
            return_value=dict(success=True, tokens=["token123"])
        )
        self.handler.provider_token = mock.MagicMock(return_value="jwt")

        with mock.patch.object(apn, "httpx", mock.MagicMock()):
            result = self.handler.send_to_tokens(
                "token123", {"alert": "Hello"}, app=mock_app
            )

        # verifies the HTTP/2 send received the app configuration and an
        # authentication function bound to the app credentials
        self.assertEqual(result["tokens"], ["token123"])
        call_args = self.handler.send_h2.call_args
        self.assertEqual(call_args[0][0], set(["token123"]))
        self.assertEqual(call_args[1]["sandbox"], True)
        self.assertEqual(call_args[1]["topic"], "pt.hive.app")
        self.assertEqual(call_args[1]["auth"](), "jwt")
        self.handler.provider_token.assert_called_with(
            "auth_key", "KEY123", "TEAM123", force=False
        )
        self.assertEqual(call_args[1]["auth"](force=True), "jwt")
        self.handler.provider_token.assert_called_with(
            "auth_key", "KEY123", "TEAM123", force=True
        )

    def test_send_to_tokens_token_without_key_id(self):
        """
        Tests send_to_tokens raises when the key id of the token based
        authentication is not defined.
        """

        self.assertRaises(
            RuntimeError,
            self.handler.send_to_tokens,
            ["token123"],
            {"alert": "Hello"},
            auth_key="auth_key",
            team_id="TEAM123",
            topic="pt.hive.app",
        )

    def test_send_to_tokens_token_without_team_id(self):
        """
        Tests send_to_tokens raises when the team id of the token based
        authentication is not defined.
        """

        self.assertRaises(
            RuntimeError,
            self.handler.send_to_tokens,
            ["token123"],
            {"alert": "Hello"},
            auth_key="auth_key",
            key_id="KEY123",
            topic="pt.hive.app",
        )

    def test_send_to_tokens_token_without_topic(self):
        """
        Tests send_to_tokens raises when the topic of the token based
        authentication is not defined, as it's required by the API.
        """

        self.assertRaises(
            RuntimeError,
            self.handler.send_to_tokens,
            ["token123"],
            {"alert": "Hello"},
            auth_key="auth_key",
            key_id="KEY123",
            team_id="TEAM123",
        )

    def test_send_to_tokens_token_without_httpx(self):
        """
        Tests send_to_tokens raises when the token based authentication is
        requested but no HTTP/2 client (httpx) is available.
        """

        with mock.patch.object(apn, "httpx", None):
            self.assertRaises(
                RuntimeError,
                self.handler.send_to_tokens,
                ["token123"],
                {"alert": "Hello"},
                auth_key="auth_key",
                key_id="KEY123",
                team_id="TEAM123",
                topic="pt.hive.app",
            )

    def test_send_to_tokens_token_without_cryptography(self):
        """
        Tests send_to_tokens raises when the token based authentication is
        requested but the cryptography library is not available.
        """

        with mock.patch.object(apn, "httpx", mock.MagicMock()):
            with mock.patch.object(apn, "cryptography", None):
                self.assertRaises(
                    RuntimeError,
                    self.handler.send_to_tokens,
                    ["token123"],
                    {"alert": "Hello"},
                    auth_key="auth_key",
                    key_id="KEY123",
                    team_id="TEAM123",
                    topic="pt.hive.app",
                )

    def test_send_to_tokens_certificate_h2(self):
        """
        Tests send_to_tokens sends through the HTTP/2 API with the certificate
        based authentication, removing the temporary files afterwards.
        """

        # captures the certificate files (and their contents) at the time
        # of the HTTP/2 send, as they are removed right after it
        captured = dict()

        def send_h2(tokens, message, **kwargs):
            cer_path, key_path = kwargs["cert"]
            captured["paths"] = (cer_path, key_path)
            captured["cer"] = open(cer_path, "rb").read()
            captured["key"] = open(key_path, "rb").read()
            captured["kwargs"] = kwargs
            return dict(success=True, tokens=list(tokens))

        self.handler.send_h2 = mock.MagicMock(side_effect=send_h2)

        with mock.patch.object(apn, "httpx", mock.MagicMock()):
            result = self.handler.send_to_tokens(
                ["token123"],
                {"alert": "Hello"},
                key_data="key",
                cer_data="cer",
                topic="pt.hive.app",
            )

        # verifies the certificate files were provided with the right contents,
        # that no token authentication was used and that they were removed
        self.assertEqual(result["tokens"], ["token123"])
        self.assertEqual(captured["cer"], b"cer")
        self.assertEqual(captured["key"], b"key")
        self.assertEqual(captured["kwargs"]["sandbox"], False)
        self.assertEqual(captured["kwargs"]["topic"], "pt.hive.app")
        self.assertEqual("auth" in captured["kwargs"], False)
        self.assertEqual(os.path.exists(captured["paths"][0]), False)
        self.assertEqual(os.path.exists(captured["paths"][1]), False)

    def test_send_to_tokens_certificate_h2_error(self):
        """
        Tests send_to_tokens removes the temporary certificate files even
        when the HTTP/2 send fails with an exception.
        """

        captured = dict()

        def send_h2(tokens, message, **kwargs):
            captured["paths"] = kwargs["cert"]
            raise RuntimeError("boom")

        self.handler.send_h2 = mock.MagicMock(side_effect=send_h2)

        with mock.patch.object(apn, "httpx", mock.MagicMock()):
            self.assertRaises(
                RuntimeError,
                self.handler.send_to_tokens,
                ["token123"],
                {"alert": "Hello"},
                key_data="key",
                cer_data="cer",
            )

        self.assertEqual(os.path.exists(captured["paths"][0]), False)

    def test_send_to_tokens_certificate_legacy(self):
        """
        Tests send_to_tokens falls back to the legacy binary protocol when
        no HTTP/2 client (httpx) is available.
        """

        # mocks the legacy client so that the finish callback of the protocol
        # is called once the loop runs, as the real protocol would do
        mock_loop = mock.MagicMock()
        mock_protocol = mock.MagicMock()
        callbacks = []
        mock_protocol.bind.side_effect = lambda name, callback: callbacks.append(
            callback
        )
        mock_loop.run_forever.side_effect = lambda: callbacks[-1](mock_protocol)

        invalid = dict()

        with mock.patch.object(apn, "httpx", None):
            with mock.patch.object(
                apn.netius.clients.APNClient,
                "notify_s",
                return_value=(mock_loop, mock_protocol),
            ) as notify_s:
                with mock.patch.object(apn.netius, "compat_loop"):
                    result = self.handler.send_to_tokens(
                        ["token123"],
                        {"alert": "Hello"},
                        key_data="key",
                        cer_data="cer",
                        sandbox=True,
                        invalid=invalid,
                    )

        # verifies the legacy client was used for the token and that the token
        # was marked as notified in the map of invalid items
        self.assertEqual(result["tokens"], ["token123"])
        self.assertEqual(invalid, {"token123": True})
        self.assertEqual(notify_s.call_args[0][0], "token123")
        self.assertEqual(notify_s.call_args[1]["sandbox"], True)

    def test_send_h2(self):
        """
        Tests send_h2 posts the notification to the production host of the
        provider API with the expected payload and headers.
        """

        mock_httpx = self._mock_httpx([200])
        invalid = dict()

        with mock.patch.object(apn, "httpx", mock_httpx):
            result = self.handler.send_h2(
                ["token123"], "Hello", topic="pt.hive.app", invalid=invalid
            )

        # verifies the HTTP/2 client creation and the request sent through it
        mock_httpx.Client.assert_called_once_with(
            http2=True, cert=None, timeout=apn.TIMEOUT
        )
        client = mock_httpx.Client.return_value
        call_args = client.post.call_args
        self.assertEqual(
            call_args[0][0], "https://api.push.apple.com/3/device/token123"
        )
        self.assertEqual(
            json.loads(call_args[1]["content"].decode("utf-8")),
            {"aps": {"alert": "Hello", "sound": "default", "badge": 0}},
        )
        self.assertEqual(call_args[1]["headers"]["apns-topic"], "pt.hive.app")
        self.assertEqual(call_args[1]["headers"]["apns-push-type"], "alert")
        self.assertEqual(call_args[1]["headers"]["apns-priority"], "10")
        self.assertEqual("authorization" in call_args[1]["headers"], False)
        client.close.assert_called_once_with()

        self.assertEqual(result["success"], True)
        self.assertEqual(result["tokens"], ["token123"])
        self.assertEqual(invalid, {"token123": True})

    def test_send_h2_sandbox(self):
        """
        Tests send_h2 posts the notification to the sandbox host, without
        the topic header when no topic is defined (certificate based).
        """

        mock_httpx = self._mock_httpx([200])

        with mock.patch.object(apn, "httpx", mock_httpx):
            self.handler.send_h2(
                ["token123"], "Hello", sandbox=True, cert=("cer", "key")
            )

        client = mock_httpx.Client.return_value
        call_args = client.post.call_args
        self.assertEqual(
            call_args[0][0], "https://api.sandbox.push.apple.com/3/device/token123"
        )
        self.assertEqual("apns-topic" in call_args[1]["headers"], False)
        self.assertEqual(mock_httpx.Client.call_args[1]["cert"], ("cer", "key"))

    def test_send_h2_auth(self):
        """
        Tests send_h2 sends the provider token as a bearer authorization.
        """

        mock_httpx = self._mock_httpx([200])
        auth = mock.MagicMock(return_value="jwt123")

        with mock.patch.object(apn, "httpx", mock_httpx):
            self.handler.send_h2(["token123"], "Hello", auth=auth)

        client = mock_httpx.Client.return_value
        headers = client.post.call_args[1]["headers"]
        self.assertEqual(headers["authorization"], "bearer jwt123")
        auth.assert_called_once_with(force=False)

    def test_send_h2_invalid(self):
        """
        Tests send_h2 skips the tokens that have already been notified.
        """

        mock_httpx = self._mock_httpx([200])

        with mock.patch.object(apn, "httpx", mock_httpx):
            result = self.handler.send_h2(
                ["token123"], "Hello", invalid={"token123": True}
            )

        client = mock_httpx.Client.return_value
        self.assertEqual(client.post.called, False)
        self.assertEqual(result["tokens"], [])
        client.close.assert_called_once_with()

    def test_send_h2_unregistered(self):
        """
        Tests send_h2 removes the subscriptions of a token that the provider
        API reports as no longer active (410 Unregistered).
        """

        mock_httpx = self._mock_httpx([(410, {"reason": "Unregistered"})])
        self.handler.unsubscribes = mock.MagicMock()
        invalid = dict()

        with mock.patch.object(apn, "httpx", mock_httpx):
            result = self.handler.send_h2(["token123"], "Hello", invalid=invalid)

        self.handler.unsubscribes.assert_called_once_with("token123")
        self.assertEqual(result["tokens"], [])
        self.assertEqual(invalid, {})

    def test_send_h2_bad_device_token(self):
        """
        Tests send_h2 removes the subscriptions of a token that the provider
        API reports as invalid (400 BadDeviceToken).
        """

        mock_httpx = self._mock_httpx([(400, {"reason": "BadDeviceToken"})])
        self.handler.unsubscribes = mock.MagicMock()

        with mock.patch.object(apn, "httpx", mock_httpx):
            result = self.handler.send_h2(["token123"], "Hello")

        self.handler.unsubscribes.assert_called_once_with("token123")
        self.assertEqual(result["tokens"], [])

    def test_send_h2_bad_request(self):
        """
        Tests send_h2 keeps the subscriptions of a token when the provider
        API rejects the request for a reason unrelated to the token.
        """

        mock_httpx = self._mock_httpx([(400, {"reason": "PayloadTooLarge"})])
        self.handler.unsubscribes = mock.MagicMock()

        with mock.patch.object(apn, "httpx", mock_httpx):
            result = self.handler.send_h2(["token123"], "Hello")

        self.assertEqual(self.handler.unsubscribes.called, False)
        self.assertEqual(result["tokens"], [])
        self.mock_owner.app.logger.warning.assert_called()

    def test_send_h2_unsubscribe_error(self):
        """
        Tests send_h2 tolerates a failure while removing the subscriptions
        of an invalid token, carrying on with the remaining tokens.
        """

        mock_httpx = self._mock_httpx([(410, {"reason": "Unregistered"})])
        self.handler.unsubscribes = mock.MagicMock(side_effect=Exception("boom"))

        with mock.patch.object(apn, "httpx", mock_httpx):
            result = self.handler.send_h2(["token123"], "Hello")

        self.assertEqual(result["success"], True)
        self.assertEqual(result["tokens"], [])

    def test_send_h2_expired_provider_token(self):
        """
        Tests send_h2 generates a new provider token and retries once when
        the provider API reports the token as expired.
        """

        mock_httpx = self._mock_httpx([(403, {"reason": "ExpiredProviderToken"}), 200])
        auth = mock.MagicMock(side_effect=lambda force=False: "new" if force else "old")
        self.handler.unsubscribes = mock.MagicMock()

        with mock.patch.object(apn, "httpx", mock_httpx):
            result = self.handler.send_h2(["token123"], "Hello", auth=auth)

        client = mock_httpx.Client.return_value
        self.assertEqual(client.post.call_count, 2)
        self.assertEqual(
            auth.call_args_list, [mock.call(force=False), mock.call(force=True)]
        )
        self.assertEqual(result["tokens"], ["token123"])
        self.assertEqual(self.handler.unsubscribes.called, False)

    def test_send_h2_expired_provider_token_twice(self):
        """
        Tests send_h2 retries only once when the provider API keeps
        rejecting the (new) provider token, not removing the device token.
        """

        mock_httpx = self._mock_httpx(
            [
                (403, {"reason": "InvalidProviderToken"}),
                (403, {"reason": "InvalidProviderToken"}),
            ]
        )
        auth = mock.MagicMock(return_value="jwt")
        self.handler.unsubscribes = mock.MagicMock()

        with mock.patch.object(apn, "httpx", mock_httpx):
            result = self.handler.send_h2(["token123"], "Hello", auth=auth)

        client = mock_httpx.Client.return_value
        self.assertEqual(client.post.call_count, 2)
        self.assertEqual(result["tokens"], [])
        self.assertEqual(self.handler.unsubscribes.called, False)

    def test_send_h2_expired_provider_token_certificate(self):
        """
        Tests send_h2 does not retry an expired provider token error when
        the certificate based authentication is in use (no token to renew).
        """

        mock_httpx = self._mock_httpx([(403, {"reason": "ExpiredProviderToken"})])

        with mock.patch.object(apn, "httpx", mock_httpx):
            result = self.handler.send_h2(["token123"], "Hello", cert=("cer", "key"))

        client = mock_httpx.Client.return_value
        self.assertEqual(client.post.call_count, 1)
        self.assertEqual(result["tokens"], [])

    def test_send_h2_error(self):
        """
        Tests send_h2 carries on with the remaining tokens when the request
        for one of them fails, closing the client at the end.
        """

        mock_httpx = self._mock_httpx([])
        client = mock_httpx.Client.return_value
        client.post.side_effect = [Exception("connection reset"), self._response(200)]

        with mock.patch.object(apn, "httpx", mock_httpx):
            result = self.handler.send_h2(["token1", "token2"], "Hello")

        self.assertEqual(client.post.call_count, 2)
        self.assertEqual(len(result["tokens"]), 1)
        client.close.assert_called_once_with()

    def test_send_h2_close_on_error(self):
        """
        Tests send_h2 closes the HTTP/2 client even when an unexpected
        error escapes the sending loop.
        """

        mock_httpx = self._mock_httpx([200])
        auth = mock.MagicMock(side_effect=ValueError("invalid key"))

        with mock.patch.object(apn, "httpx", mock_httpx):
            self.assertRaises(
                ValueError, self.handler.send_h2, ["token123"], "Hello", auth=auth
            )

        mock_httpx.Client.return_value.close.assert_called_once_with()

    @unittest.skipIf(cryptography == None, "cryptography library not available")
    def test_provider_token(self):
        """
        Tests provider_token builds an ES256 signed JWT, with the key id in
        the header and the team id as the issuer, valid for the key.
        """

        private_key, pem = self._generate_key()

        with mock.patch.object(apn.time, "time", return_value=1000.0):
            token = self.handler.provider_token(pem, "KEY123", "TEAM123")

        # decodes the header and the claims of the token and verifies them
        header, claims, signature = token.split(".")
        self.assertEqual(
            json.loads(self._decode(header)), {"alg": "ES256", "kid": "KEY123"}
        )
        self.assertEqual(
            json.loads(self._decode(claims)), {"iss": "TEAM123", "iat": 1000}
        )

        # verifies the (raw) signature against the public key, raising in
        # case the signature is not valid for the signing input
        raw = self._decode(signature)
        self.assertEqual(len(raw), 64)
        r = int(binascii.hexlify(raw[:32]), 16)
        s = int(binascii.hexlify(raw[32:]), 16)
        der = cryptography.hazmat.primitives.asymmetric.utils.encode_dss_signature(r, s)
        private_key.public_key().verify(
            der,
            ("%s.%s" % (header, claims)).encode("utf-8"),
            cryptography.hazmat.primitives.asymmetric.ec.ECDSA(
                cryptography.hazmat.primitives.hashes.SHA256()
            ),
        )

    @unittest.skipIf(cryptography == None, "cryptography library not available")
    def test_provider_token_cached(self):
        """
        Tests provider_token re-uses the token while it's still valid, as
        Apple refuses tokens refreshed too frequently.
        """

        _private_key, pem = self._generate_key()

        with mock.patch.object(apn.time, "time", return_value=1000.0):
            first = self.handler.provider_token(pem, "KEY123", "TEAM123")
        with mock.patch.object(apn.time, "time", return_value=1000.0 + 1200):
            second = self.handler.provider_token(pem, "KEY123", "TEAM123")

        self.assertEqual(first, second)

    @unittest.skipIf(cryptography == None, "cryptography library not available")
    def test_provider_token_refresh(self):
        """
        Tests provider_token generates a new token once the previous one
        reaches its time to live, and keeps tokens of other keys apart.
        """

        _private_key, pem = self._generate_key()

        with mock.patch.object(apn.time, "time", return_value=1000.0):
            first = self.handler.provider_token(pem, "KEY123", "TEAM123")
            other = self.handler.provider_token(pem, "KEY456", "TEAM123")
        with mock.patch.object(apn.time, "time", return_value=1000.0 + apn.TOKEN_TTL):
            second = self.handler.provider_token(pem, "KEY123", "TEAM123")

        self.assertNotEqual(first, second)
        self.assertNotEqual(first, other)
        claims = json.loads(self._decode(second.split(".")[1]))
        self.assertEqual(claims["iat"], 1000 + apn.TOKEN_TTL)

    @unittest.skipIf(cryptography == None, "cryptography library not available")
    def test_provider_token_force(self):
        """
        Tests provider_token generates a new token when forced, even if the
        previous one is still valid.
        """

        _private_key, pem = self._generate_key()

        with mock.patch.object(apn.time, "time", return_value=1000.0):
            first = self.handler.provider_token(pem, "KEY123", "TEAM123")
        with mock.patch.object(apn.time, "time", return_value=1001.0):
            second = self.handler.provider_token(pem, "KEY123", "TEAM123", force=True)

        self.assertNotEqual(first, second)

    @unittest.skipIf(cryptography == None, "cryptography library not available")
    def test_provider_token_invalid_key(self):
        """
        Tests provider_token raises for an invalid authentication key and
        does not cache anything for it.
        """

        self.assertRaises(
            ValueError,
            self.handler.provider_token,
            "-----BEGIN PRIVATE KEY-----\ninvalid\n-----END PRIVATE KEY-----",
            "KEY123",
            "TEAM123",
        )
        self.assertEqual(self.handler.provider_tokens, {})

    def test_payload(self):
        """
        Tests _payload uses a string message as the alert of the payload,
        with the same defaults as the legacy binary protocol.
        """

        payload = self.handler._payload("Hello")

        self.assertEqual(type(payload), bytes)
        self.assertEqual(
            json.loads(payload.decode("utf-8")),
            {"aps": {"alert": "Hello", "sound": "default", "badge": 0}},
        )

    def test_payload_alert(self):
        """
        Tests _payload uses a dictionary message without the aps key as
        the (structured) alert of the payload.
        """

        payload = self.handler._payload({"title": "Sales", "body": "Hello"})

        self.assertEqual(
            json.loads(payload.decode("utf-8"))["aps"]["alert"],
            {"title": "Sales", "body": "Hello"},
        )

    def test_payload_complete(self):
        """
        Tests _payload uses a complete APN payload (with the aps key) as is.
        """

        message = {"aps": {"alert": "Hello", "badge": 3}, "store": 1}
        payload = self.handler._payload(message)

        self.assertEqual(json.loads(payload.decode("utf-8")), message)

    def test_reason(self):
        """
        Tests _reason retrieves the reason from the JSON error body.
        """

        response = self._response(400, {"reason": "BadDeviceToken"})

        self.assertEqual(self.handler._reason(response), "BadDeviceToken")

    def test_reason_invalid(self):
        """
        Tests _reason falls back to the response text for bodies that are
        not a JSON error structure (invalid JSON, list or no reason).
        """

        response = self._response(500)
        response.json.side_effect = ValueError("invalid JSON")
        response.text = "Internal Server Error"
        self.assertEqual(self.handler._reason(response), "Internal Server Error")

        response = self._response(500, ["error"])
        response.text = '["error"]'
        self.assertEqual(self.handler._reason(response), '["error"]')

        response = self._response(500, {"error": "other"})
        response.text = "{}"
        self.assertEqual(self.handler._reason(response), "{}")

    def test_base64(self):
        """
        Tests _base64 encodes using the URL safe alphabet without padding.
        """

        self.assertEqual(self.handler._base64("a"), "YQ")
        self.assertEqual(self.handler._base64(b"\xfb\xff"), "-_8")
        self.assertEqual(self.handler._base64(""), "")

    def _mock_httpx(self, responses):
        mock_httpx = mock.MagicMock()
        client = mock_httpx.Client.return_value
        client.post.side_effect = [
            self._response(*(value if isinstance(value, tuple) else (value,)))
            for value in responses
        ]
        return mock_httpx

    def _response(self, status_code, body=None):
        response = mock.MagicMock()
        response.status_code = status_code
        response.json.return_value = body if body != None else {}
        response.text = json.dumps(body) if body != None else ""
        return response

    def _generate_key(self):
        private_key = cryptography.hazmat.primitives.asymmetric.ec.generate_private_key(
            cryptography.hazmat.primitives.asymmetric.ec.SECP256R1()
        )
        pem = private_key.private_bytes(
            encoding=cryptography.hazmat.primitives.serialization.Encoding.PEM,
            format=cryptography.hazmat.primitives.serialization.PrivateFormat.PKCS8,
            encryption_algorithm=cryptography.hazmat.primitives.serialization.NoEncryption(),
        ).decode("utf-8")
        return private_key, pem

    def _decode(self, value):
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


if __name__ == "__main__":
    unittest.main()
