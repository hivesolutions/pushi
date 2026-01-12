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

import appier

import pushi


class MessagingController(appier.Controller):
    """
    Controller for direct message sending through various adapters
    without requiring pub/sub subscriptions.

    Provides HTTP endpoints for sending messages via APN, SMTP,
    Webhook, and Web Push adapters using the Messenger API.
    """

    @appier.private
    @appier.route("/messaging/send", "POST")
    def send(self):
        """
        Sends a message through one or more adapters.

        Accepts a JSON payload with adapter configuration and targets,
        allowing the same message to be sent through multiple channels.

        Example payload:
        {
            "adapters": ["apn", "email", "web_push"],
            "data": {"title": "Hello", "body": "World"},
            "apn_tokens": ["device_token_1"],
            "email_to": ["user@example.com"],
            "email_subject": "Notification",
            "web_push_subscriptions": [
                {"endpoint": "...", "p256dh": "...", "auth": "..."}
            ]
        }
        """

        # retrieves the app from the current session
        app_id = self.session.get("app_id", None)
        app = pushi.App.get(ident=app_id)

        # retrieves the JSON payload from the request
        data = self.request.get_json() or dict()

        # extracts the adapters to use (required)
        adapters = data.get("adapters", None)
        if not adapters:
            raise appier.OperationalError(message="No adapters specified")

        # creates the messenger instance bound to the app
        messenger = pushi.Messenger(app=app, logger=self.owner.logger)

        # sends the message through the specified adapters
        result = messenger.send(
            adapters=adapters,
            data=data.get("data"),
            apn_tokens=data.get("apn_tokens"),
            apn_message=data.get("apn_message"),
            email_to=data.get("email_to"),
            email_subject=data.get("email_subject"),
            email_body=data.get("email_body"),
            email_html=data.get("email_html", False),
            webhook_urls=data.get("webhook_urls"),
            webhook_headers=data.get("webhook_headers"),
            webhook_method=data.get("webhook_method", "POST"),
            web_push_subscriptions=data.get("web_push_subscriptions"),
            web_push_message=data.get("web_push_message"),
        )

        return result

    @appier.private
    @appier.route("/messaging/apn", "POST")
    def send_apn(self):
        """
        Sends an Apple Push Notification to one or more devices.

        Example payload:
        {
            "tokens": ["device_token_1", "device_token_2"],
            "message": {"alert": "Hello!", "badge": 1}
        }
        """

        # retrieves the app from the current session
        app_id = self.session.get("app_id", None)
        app = pushi.App.get(ident=app_id)

        # retrieves the JSON payload from the request
        data = self.request.get_json() or dict()

        # extracts required parameters
        tokens = data.get("tokens")
        message = data.get("message")

        if not tokens:
            raise appier.OperationalError(message="No device tokens specified")
        if not message:
            raise appier.OperationalError(message="No message specified")

        # creates the messenger instance and sends the notification
        messenger = pushi.Messenger(app=app, logger=self.owner.logger)
        result = messenger.send_apn(
            tokens=tokens,
            message=message,
            key_data=data.get("key_data"),
            cer_data=data.get("cer_data"),
            sandbox=data.get("sandbox"),
        )

        return result

    @appier.private
    @appier.route("/messaging/email", "POST")
    def send_email(self):
        """
        Sends an email to one or more recipients.

        Example payload:
        {
            "to": ["user@example.com"],
            "subject": "Hello",
            "body": "This is a test message"
        }
        """

        # retrieves the app from the current session
        app_id = self.session.get("app_id", None)
        app = pushi.App.get(ident=app_id)

        # retrieves the JSON payload from the request
        data = self.request.get_json() or dict()

        # extracts required parameters
        to = data.get("to")
        subject = data.get("subject")
        body = data.get("body")

        if not to:
            raise appier.OperationalError(message="No recipient specified")
        if not subject:
            raise appier.OperationalError(message="No subject specified")
        if not body:
            raise appier.OperationalError(message="No body specified")

        # creates the messenger instance and sends the email
        messenger = pushi.Messenger(app=app, logger=self.owner.logger)
        result = messenger.send_email(
            to=to,
            subject=subject,
            body=body,
            smtp_host=data.get("smtp_host"),
            smtp_port=data.get("smtp_port"),
            smtp_user=data.get("smtp_user"),
            smtp_password=data.get("smtp_password"),
            smtp_starttls=data.get("smtp_starttls"),
            smtp_sender=data.get("smtp_sender"),
            smtp_url=data.get("smtp_url"),
            html=data.get("html", False),
        )

        return result

    @appier.private
    @appier.route("/messaging/webhook", "POST")
    def send_webhook(self):
        """
        Sends an HTTP request to a webhook endpoint.

        Example payload:
        {
            "url": "https://example.com/webhook",
            "data": {"event": "user.created", "user_id": 123}
        }
        """

        # retrieves the JSON payload from the request
        data = self.request.get_json() or dict()

        # extracts required parameters
        url = data.get("url")
        payload = data.get("data")

        if not url:
            raise appier.OperationalError(message="No webhook URL specified")
        if payload is None:
            raise appier.OperationalError(message="No data specified")

        # creates the messenger instance and sends the webhook
        messenger = pushi.Messenger(logger=self.owner.logger)
        result = messenger.send_webhook(
            url=url,
            data=payload,
            headers=data.get("headers"),
            method=data.get("method", "POST"),
        )

        return result

    @appier.private
    @appier.route("/messaging/web_push", "POST")
    def send_web_push(self):
        """
        Sends a Web Push notification to a browser subscription.

        Example payload:
        {
            "endpoint": "https://fcm.googleapis.com/...",
            "p256dh": "...",
            "auth": "...",
            "message": {"title": "Hello", "body": "World"}
        }
        """

        # retrieves the app from the current session
        app_id = self.session.get("app_id", None)
        app = pushi.App.get(ident=app_id)

        # retrieves the JSON payload from the request
        data = self.request.get_json() or dict()

        # extracts required parameters
        endpoint = data.get("endpoint")
        p256dh = data.get("p256dh")
        auth = data.get("auth")
        message = data.get("message")

        if not endpoint:
            raise appier.OperationalError(message="No endpoint specified")
        if not p256dh:
            raise appier.OperationalError(message="No p256dh key specified")
        if not auth:
            raise appier.OperationalError(message="No auth secret specified")

        # creates the messenger instance and sends the notification
        messenger = pushi.Messenger(app=app, logger=self.owner.logger)
        result = messenger.send_web_push(
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            message=message,
            vapid_private_key=data.get("vapid_private_key"),
            vapid_email=data.get("vapid_email"),
        )

        return result
