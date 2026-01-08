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

"""
Email subscription example that registers an email address to receive
notifications when events are published to a channel.

Initializes the API client with application credentials and subscribes
the provided email address to the "notifications" channel. When events
are triggered on this channel, an email will be sent via SMTP.

Run from the examples/mail directory with:
    python subscribe.py user@example.com

Before running:
    1. Update app_id, app_key, app_secret with your Pushi credentials
    2. Update base_url to point to your Pushi server
    3. Ensure SMTP is configured on the Pushi server

Requires: `pip install pushi`
"""

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import sys

import pushi

# initializes the API client with the application
# credentials obtained from the Pushi server
api = pushi.API(
    app_id="YOUR_APP_ID",
    app_key="YOUR_APP_KEY",
    app_secret="YOUR_APP_SECRET",
    base_url="http://localhost:8080/",
)

# retrieves the email address from command line arguments
# or uses a default value if not provided
email = sys.argv[1] if len(sys.argv) > 1 else "user@example.com"

# subscribes the email address to the notifications channel
# when events are triggered on this channel, an email will be sent
print("Subscribing %s to 'notifications' channel..." % email)
result = api.post(
    api.base_url + "mails",
    data_j=dict(email=email, event="notifications"),
)
print("Subscription created with ID: %s" % result.get("id"))
