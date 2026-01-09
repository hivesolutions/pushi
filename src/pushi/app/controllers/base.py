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

import base64

import appier

import pushi


class BaseController(appier.Controller):

    @appier.private
    @appier.route("/vapid_key", "GET")
    def vapid_key(self):
        """
        Retrieves the VAPID public key for Web Push subscription.

        The public key is derived from the configured VAPID private key
        and is needed by browsers to subscribe to push notifications
        using the Web Push API (applicationServerKey).

        :rtype: Dictionary
        :return: Dictionary containing the VAPID public key in base64url format.
        """

        # retrieves the app from the current session
        app_id = self.session.get("app_id", None)
        app = pushi.App.get(ident=app_id)
        if not app.vapid_key:
            raise appier.OperationalError(
                message="VAPID credentials not configured for this app"
            )

        # derives the public key from the private key using
        # the py_vapid library, which handles both PEM and
        # raw key formats
        try:
            import py_vapid
        except ImportError:
            raise appier.OperationalError(
                message="py_vapid library not available, required for Web Push"
            )

        try:
            import cryptography.hazmat.primitives
        except ImportError:
            raise appier.OperationalError(
                message="cryptography library not available, required for Web Push"
            )

        try:
            # detects the key format and uses the appropriate
            # method to load it (PEM or raw base64url)
            if pushi.is_pem_key(app.vapid_key):
                vapid = py_vapid.Vapid.from_pem(app.vapid_key.encode("utf-8"))
            else:
                vapid = py_vapid.Vapid.from_string(app.vapid_key)

            # serializes the public key to uncompressed point format
            # and encodes it as base64url for browser consumption
            public_bytes = vapid.public_key.public_bytes(
                encoding=cryptography.hazmat.primitives.serialization.Encoding.X962,
                format=cryptography.hazmat.primitives.serialization.PublicFormat.UncompressedPoint,
            )
            public_key = (
                base64.urlsafe_b64encode(public_bytes).decode("utf-8").rstrip("=")
            )
        except Exception as exception:
            raise appier.OperationalError(
                message="Failed to derive VAPID public key: %s" % str(exception)
            )

        return dict(vapid_public_key=public_key)
