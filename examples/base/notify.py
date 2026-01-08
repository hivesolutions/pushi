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
Web Push notification example that sends push notifications to all
subscribers of a channel using the Pushi API client.

Initializes the API client with application credentials and triggers
an event on the "notifications" channel with a full notification
payload including title, body, icon, vibration pattern, and click URL.

Run from the examples/web-push directory with:
    python notify.py

Before running:
    1. Update app_id, app_key, app_secret with your Pushi credentials
    2. Update base_url to point to your Pushi server
    3. Ensure at least one browser client has subscribed via index.html

Requires: `pip install pushi`
"""

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import pushi

# initializes the API client with the application
# credentials obtained from the Pushi server
api = pushi.API(
    app_id="YOUR_APP_ID",
    app_key="YOUR_APP_KEY",
    app_secret="YOUR_APP_SECRET",
    base_url="http://localhost:8080/",
)

# sends a Web Push notification to all subscribers
# of the "notifications" channel with full payload
print("Sending Web Push notification...")
api.trigger_event(
    channel="notifications",
    data={
        "title": "Hello from Pushi!",
        "body": "This is a test Web Push notification.",
        "icon": "icon.svg",
        "vibrate": [200, 100, 200, 100, 400],
        "tag": "pushi-notification",
        "url": "https://github.com/hivesolutions/pushi",
    },
)
print("Notification sent!")
