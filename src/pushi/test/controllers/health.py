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

from pushi.app.controllers import health


class HealthControllerTest(unittest.TestCase):
    """
    Unit tests for the HealthController class.

    Tests the health check endpoints functionality including
    basic health, detailed health, liveness and readiness probes.
    """

    def setUp(self):
        """
        Sets up test fixtures before each test method.
        """

        # creates a mock owner (app) with required attributes
        self.mock_owner = mock.MagicMock()
        self.mock_owner._version.return_value = "0.4.8"

        # creates the controller instance
        self.controller = health.HealthController(owner=self.mock_owner)

    def test_health(self):
        """
        Tests the basic health check endpoint.
        """

        result = self.controller.health()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["service"], "pushi")
        self.assertEqual(result["version"], "0.4.8")

    def test_health_live(self):
        """
        Tests the liveness probe endpoint.
        """

        result = self.controller.health_live()

        self.assertEqual(result["status"], "ok")

    @mock.patch("pushi.App")
    def test_health_ready_success(self, mock_app_model):
        """
        Tests the readiness probe endpoint when all checks pass.
        """

        # mocks successful database check
        mock_app_model.count.return_value = 5

        # mocks successful WebSocket server check
        mock_state = mock.MagicMock()
        mock_server = mock.MagicMock()
        mock_server.sockets = {"socket1": mock.MagicMock()}
        mock_server.count = 100
        mock_server.info_dict.return_value = {"status": "running"}
        mock_state.server = mock_server
        self.mock_owner.state = mock_state

        result = self.controller.health_ready()

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["ready"])

    @mock.patch("pushi.App")
    def test_health_ready_database_failure(self, mock_app_model):
        """
        Tests the readiness probe endpoint when database is unavailable.
        """

        # mocks database failure
        mock_app_model.count.side_effect = Exception("Database connection failed")

        # expects an OperationalError to be raised
        with self.assertRaises(Exception) as context:
            self.controller.health_ready()

        self.assertIn("Database not ready", str(context.exception))

    @mock.patch("pushi.App")
    def test_health_ready_websocket_not_initialized(self, mock_app_model):
        """
        Tests the readiness probe endpoint when WebSocket server is not initialized.
        """

        # mocks successful database check
        mock_app_model.count.return_value = 5

        # mocks missing state
        self.mock_owner.state = None

        # expects an OperationalError to be raised
        with self.assertRaises(Exception) as context:
            self.controller.health_ready()

        self.assertIn("WebSocket server not ready", str(context.exception))

    @mock.patch("pushi.App")
    def test_health_detailed_all_ok(self, mock_app_model):
        """
        Tests the detailed health check when all components are healthy.
        """

        # mocks successful database check
        mock_app_model.count.return_value = 5

        # mocks successful WebSocket server
        mock_state = mock.MagicMock()
        mock_server = mock.MagicMock()
        mock_server.sockets = {"socket1": mock.MagicMock(), "socket2": mock.MagicMock()}
        mock_server.count = 150
        mock_server.info_dict.return_value = {"status": "running"}
        mock_state.server = mock_server

        # mocks handlers
        mock_handler1 = mock.MagicMock()
        mock_handler1.name = "apn"
        mock_handler1.tokens = {"app1": {"event1": ["token1", "token2"]}}

        mock_handler2 = mock.MagicMock()
        mock_handler2.name = "web_push"
        mock_handler2.subs = {"app1": {"event1": ["sub1", "sub2", "sub3"]}}

        mock_state.handlers = [mock_handler1, mock_handler2]
        self.mock_owner.state = mock_state

        result = self.controller.health_detailed()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["service"], "pushi")
        self.assertEqual(result["version"], "0.4.8")
        self.assertIn("timestamp", result)
        self.assertIn("checks", result)

        # verifies database check
        self.assertEqual(result["checks"]["database"]["status"], "ok")
        self.assertEqual(result["checks"]["database"]["app_count"], 5)
        self.assertIn("latency_ms", result["checks"]["database"])

        # verifies WebSocket check
        self.assertEqual(result["checks"]["websocket"]["status"], "ok")
        self.assertEqual(result["checks"]["websocket"]["connections"], 2)
        self.assertEqual(result["checks"]["websocket"]["messages_sent"], 150)

        # verifies handlers check
        self.assertEqual(result["checks"]["handlers"]["status"], "ok")
        self.assertEqual(len(result["checks"]["handlers"]["handlers"]), 2)

    @mock.patch("pushi.App")
    def test_health_detailed_degraded(self, mock_app_model):
        """
        Tests the detailed health check when some components are degraded.
        """

        # mocks database failure
        mock_app_model.count.side_effect = Exception("Connection timeout")

        # mocks successful WebSocket server
        mock_state = mock.MagicMock()
        mock_server = mock.MagicMock()
        mock_server.sockets = {}
        mock_server.count = 0
        mock_server.info_dict.return_value = {}
        mock_state.server = mock_server
        mock_state.handlers = []
        self.mock_owner.state = mock_state

        result = self.controller.health_detailed()

        # status should be degraded due to database failure
        self.assertEqual(result["status"], "degraded")
        self.assertEqual(result["checks"]["database"]["status"], "error")
        self.assertIn("Connection timeout", result["checks"]["database"]["error"])

    @mock.patch("pushi.App")
    def test_check_database_success(self, mock_app_model):
        """
        Tests the database check helper method when successful.
        """

        mock_app_model.count.return_value = 10

        result = self.controller._check_database()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["app_count"], 10)
        self.assertIn("latency_ms", result)
        self.assertIsInstance(result["latency_ms"], float)

    @mock.patch("pushi.App")
    def test_check_database_failure(self, mock_app_model):
        """
        Tests the database check helper method when it fails.
        """

        mock_app_model.count.side_effect = Exception("Network error")

        result = self.controller._check_database()

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "Network error")
        self.assertIn("latency_ms", result)

    def test_check_websocket_server_no_state(self):
        """
        Tests WebSocket server check when state is not initialized.
        """

        self.mock_owner.state = None

        result = self.controller._check_websocket_server()

        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["error"], "State not initialized")

    def test_check_websocket_server_no_server(self):
        """
        Tests WebSocket server check when server is not initialized.
        """

        mock_state = mock.MagicMock()
        mock_state.server = None
        self.mock_owner.state = mock_state

        result = self.controller._check_websocket_server()

        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["error"], "WebSocket server not initialized")

    def test_check_websocket_server_success(self):
        """
        Tests WebSocket server check when server is healthy.
        """

        mock_state = mock.MagicMock()
        mock_server = mock.MagicMock()
        mock_server.sockets = {"s1": mock.MagicMock(), "s2": mock.MagicMock()}
        mock_server.count = 42
        mock_server.info_dict.return_value = {"port": 9090}
        mock_state.server = mock_server
        self.mock_owner.state = mock_state

        result = self.controller._check_websocket_server()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["connections"], 2)
        self.assertEqual(result["messages_sent"], 42)
        self.assertEqual(result["info"]["port"], 9090)

    def test_check_handlers_no_state(self):
        """
        Tests handlers check when state is not initialized.
        """

        self.mock_owner.state = None

        result = self.controller._check_handlers()

        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["error"], "State not initialized")

    def test_check_handlers_no_handlers(self):
        """
        Tests handlers check when no handlers are registered.
        """

        mock_state = mock.MagicMock()
        mock_state.handlers = []
        self.mock_owner.state = mock_state

        result = self.controller._check_handlers()

        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["error"], "No handlers registered")

    def test_check_handlers_success(self):
        """
        Tests handlers check when handlers are healthy.
        """

        mock_state = mock.MagicMock()

        mock_handler = mock.MagicMock()
        mock_handler.name = "web_push"
        mock_handler.subs = {
            "app1": {"event1": ["sub1", "sub2"], "event2": ["sub3"]},
            "app2": {"event1": ["sub4"]},
        }

        mock_state.handlers = [mock_handler]
        self.mock_owner.state = mock_state

        result = self.controller._check_handlers()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["handlers"]), 1)
        self.assertEqual(result["handlers"][0]["name"], "web_push")
        self.assertEqual(result["handlers"][0]["status"], "ok")
        self.assertEqual(result["handlers"][0]["stats"]["subscription_count"], 4)
        self.assertEqual(result["handlers"][0]["stats"]["app_count"], 2)

    def test_check_handler_with_tokens(self):
        """
        Tests handler check for handlers with token-based subscriptions (APN).
        """

        mock_handler = mock.MagicMock()
        mock_handler.name = "apn"
        mock_handler.tokens = {
            "app1": {"event1": ["token1", "token2", "token3"]},
        }
        # removes subs attribute to test token counting
        del mock_handler.subs

        result = self.controller._check_handler(mock_handler)

        self.assertEqual(result["name"], "apn")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["stats"]["token_count"], 3)

    def test_check_handler_exception(self):
        """
        Tests handler check when an exception occurs.
        """

        mock_handler = mock.MagicMock()
        mock_handler.name = "broken_handler"

        # makes subs raise an exception when accessed
        type(mock_handler).subs = mock.PropertyMock(
            side_effect=Exception("Handler error")
        )

        result = self.controller._check_handler(mock_handler)

        self.assertEqual(result["name"], "broken_handler")
        self.assertEqual(result["status"], "error")
        self.assertIn("Handler error", result["error"])
