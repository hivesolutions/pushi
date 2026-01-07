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

import pushi

# initializes the API client with the application
# credentials obtained from the Pushi server
api = pushi.API(
    app_id="YOUR_APP_ID",
    app_key="YOUR_APP_KEY",
    app_secret="YOUR_APP_SECRET",
    base_url="https://localhost:9090/",
)

# retrieves the VAPID public key that is required
# by browsers to subscribe to push notifications
vapid_info = api.get_vapid_public_key()
print("VAPID Public Key:", vapid_info["vapid_public_key"])

# subscribes a browser endpoint to notifications,
# these values come from the browser's PushSubscription
# object obtained via the Web Push API
result = api.create_web_push(
    endpoint="https://fcm.googleapis.com/fcm/send/...",
    p256dh="BNcRdreALRFX...",
    auth="tBHItJI5...",
    event="notifications",
)
print("Subscribed:", result)

# lists all the Web Push subscriptions currently
# registered for the application
subscriptions = api.list_web_pushes()
print("Subscriptions:", subscriptions)

# unsubscribes the endpoint from the notifications
# event, removing it from the server
api.delete_web_push(
    endpoint="https://fcm.googleapis.com/fcm/send/...", event="notifications"
)
print("Unsubscribed")
