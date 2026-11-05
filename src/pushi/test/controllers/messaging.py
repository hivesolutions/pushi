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

from pushi.app.controllers import messaging


class MessagingControllerTest(unittest.TestCase):
    """
    Unit tests for the MessagingController class.

    Tests the direct messaging REST API endpoints functionality, with a
    focus on the APN credentials that may be provided in the JSON body.
    """

    def setUp(self):
        """
        Sets up test fixtures before each test method.
        """

        # creates a mock owner (app) with required attributes
        self.mock_owner = mock.MagicMock()

        # creates the controller instance with an application selected
        self.controller = messaging.MessagingController(owner=self.mock_owner)
        self.controller.session = dict(app_id="app123")
        self.controller.request = mock.MagicMock()

    def test_send_apn(self):
        """
        Tests that the APN endpoint provides both the certificate and the
        token based credentials of the JSON body to the messenger.
        """

        self.controller.request.get_json.return_value = dict(
            tokens=["token123"],
            message="Hello",
            sandbox=True,
            auth_key="auth_key",
            key_id="KEY123",
            team_id="TEAM123",
            topic="pt.hive.app",
        )

        with mock.patch.object(messaging.pushi, "App") as mock_app_model:
            with mock.patch.object(messaging.pushi, "Messenger") as mock_messenger:
                self.controller.send_apn()

        # verifies the messenger was created for the selected application and
        # that every credential was provided to the APN send operation
        mock_app_model.get.assert_called_once_with(ident="app123")
        mock_messenger.return_value.send_apn.assert_called_once_with(
            tokens=["token123"],
            message="Hello",
            key_data=None,
            cer_data=None,
            sandbox=True,
            auth_key="auth_key",
            key_id="KEY123",
            team_id="TEAM123",
            topic="pt.hive.app",
        )


if __name__ == "__main__":
    unittest.main()
