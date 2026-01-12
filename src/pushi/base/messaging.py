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

from . import apn
from . import smtp
from . import web
from . import web_push


class Messenger(object):
    """
    Direct messaging API for sending messages through various
    adapters without requiring pub/sub subscriptions.

    Provides an agnostic interface for sending messages to specific
    targets using APN, SMTP, Webhook, or Web Push adapters.
    Configuration is pulled from an App instance when provided.

    This class delegates to the underlying handler implementations
    to avoid code duplication and ensure consistent behavior.
    """

    ADAPTERS = ("apn", "email", "webhook", "web_push")

    def __init__(self, app=None, logger=None):
        self.app = app
        self.logger = logger or _NullLogger()

        # creates lightweight handler instances for delegation
        # these handlers don't have an owner (state) since we're
        # using them for direct messaging only
        self._apn_handler = _StandaloneAPNHandler(self.logger)
        self._smtp_handler = _StandaloneSMTPHandler(self.logger)
        self._web_handler = _StandaloneWebHandler(self.logger)
        self._web_push_handler = _StandaloneWebPushHandler(self.logger)

    def send(
        self,
        adapters,
        data=None,
        apn_tokens=None,
        apn_message=None,
        email_to=None,
        email_subject=None,
        email_body=None,
        email_html=False,
        webhook_urls=None,
        webhook_headers=None,
        webhook_method="POST",
        web_push_subscriptions=None,
        web_push_message=None,
        **kwargs
    ):
        """
        Sends a message through one or more adapters with a unified payload.

        Allows sending the same content through multiple channels
        simultaneously using a common data payload with adapter-specific
        overrides available for each channel type.

        :type adapters: String/List
        :param adapters: Adapter(s) to use (apn, email, webhook, web_push).
        :type data: Dictionary
        :param data: Base payload data used as message content.
        :type apn_tokens: List
        :param apn_tokens: APN device tokens to send to.
        :type apn_message: Dictionary
        :param apn_message: Override message for APN (defaults to data).
        :type email_to: String/List
        :param email_to: Email recipient(s).
        :type email_subject: String
        :param email_subject: Email subject line.
        :type email_body: String
        :param email_body: Email body (defaults to JSON of data).
        :type email_html: bool
        :param email_html: Whether email body is HTML.
        :type webhook_urls: List
        :param webhook_urls: Webhook URLs to POST to.
        :type webhook_headers: Dictionary
        :param webhook_headers: Additional headers for webhook requests.
        :type webhook_method: String
        :param webhook_method: HTTP method for webhooks (default: POST).
        :type web_push_subscriptions: List
        :param web_push_subscriptions: Web Push subscription dicts with
        endpoint, p256dh, and auth keys.
        :type web_push_message: Dictionary
        :param web_push_message: Override message for Web Push.
        :rtype: Dictionary
        :return: Results dictionary with status per adapter.
        """

        # normalizes adapters to list for iteration
        if isinstance(adapters, str):
            adapters = [adapters]

        results = {}

        for adapter in adapters:
            adapter = adapter.lower()
            try:
                if adapter == "apn":
                    if apn_tokens:
                        result = self.send_apn(
                            tokens=apn_tokens, message=apn_message or data, **kwargs
                        )
                        results["apn"] = result

                elif adapter in ("email", "smtp"):
                    if email_to:
                        body = email_body
                        if body is None and data:
                            body = json.dumps(data, indent=2)
                        result = self.send_email(
                            to=email_to,
                            subject=email_subject or "Notification",
                            body=body or "",
                            html=email_html,
                            **kwargs
                        )
                        results["email"] = result

                elif adapter in ("webhook", "web"):
                    if webhook_urls:
                        result = self.send_webhook(
                            urls=webhook_urls,
                            data=data or {},
                            headers=webhook_headers,
                            method=webhook_method,
                        )
                        results["webhook"] = result

                elif adapter in ("web_push", "webpush"):
                    if web_push_subscriptions:
                        result = self.send_web_push(
                            subscriptions=web_push_subscriptions,
                            message=web_push_message or data,
                            **kwargs
                        )
                        results["web_push"] = result

                else:
                    results[adapter] = dict(
                        success=False, error="Unknown adapter: %s" % adapter
                    )

            except Exception as exception:
                results[adapter] = dict(success=False, error=str(exception))

        return results

    def send_apn(
        self,
        tokens,
        message,
        key_data=None,
        cer_data=None,
        sandbox=None,
    ):
        """
        Sends Apple Push Notifications to one or more devices.

        Configuration is pulled from the App instance if not provided
        explicitly through the method parameters.

        :type tokens: String/List
        :param tokens: APN device token(s) to send to.
        :type message: Dictionary/String
        :param message: Notification payload with APN fields.
        :type key_data: String
        :param key_data: PEM-encoded private key (defaults to app.apn_key).
        :type cer_data: String
        :param cer_data: PEM-encoded certificate (defaults to app.apn_cer).
        :type sandbox: bool
        :param sandbox: Use sandbox environment (defaults to app.apn_sandbox).
        :rtype: Dictionary
        :return: Result with success status and sent tokens.
        """

        return self._apn_handler.send_to_tokens(
            tokens=tokens,
            message=message,
            app=self.app,
            key_data=key_data,
            cer_data=cer_data,
            sandbox=sandbox,
        )

    def send_email(
        self,
        to,
        subject,
        body,
        smtp_host=None,
        smtp_port=None,
        smtp_user=None,
        smtp_password=None,
        smtp_starttls=None,
        smtp_sender=None,
        html=False,
    ):
        """
        Sends an email to one or more recipients.

        Configuration is pulled from the App instance or environment
        variables if not provided explicitly through parameters.

        :type to: String/List
        :param to: Recipient email address(es).
        :type subject: String
        :param subject: Email subject line.
        :type body: String
        :param body: Email body content.
        :type smtp_host: String
        :param smtp_host: SMTP server hostname.
        :type smtp_port: int
        :param smtp_port: SMTP server port.
        :type smtp_user: String
        :param smtp_user: SMTP username for authentication.
        :type smtp_password: String
        :param smtp_password: SMTP password for authentication.
        :type smtp_starttls: bool
        :param smtp_starttls: Whether to use STARTTLS.
        :type smtp_sender: String
        :param smtp_sender: Sender email address.
        :type html: bool
        :param html: Whether body is HTML content.
        :rtype: Dictionary
        :return: Result with success status and recipients.
        """

        return self._smtp_handler.send_to_emails(
            emails=to,
            subject=subject,
            body=body,
            app=self.app,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            smtp_starttls=smtp_starttls,
            smtp_sender=smtp_sender,
            html=html,
        )

    def send_webhook(
        self,
        urls,
        data,
        headers=None,
        method="POST",
    ):
        """
        Sends HTTP requests to one or more webhook endpoints.

        :type urls: String/List
        :param urls: Webhook URL(s) to send the request to.
        :type data: Dictionary/String
        :param data: Data to send (dictionaries are JSON-encoded).
        :type headers: Dictionary
        :param headers: Additional headers to include.
        :type method: String
        :param method: HTTP method to use (default: POST).
        :rtype: Dictionary
        :return: Result with success status and sent URLs.
        """

        return self._web_handler.send_to_urls(
            urls=urls,
            data=data,
            headers=headers,
            method=method,
        )

    def send_web_push(
        self,
        subscriptions,
        message,
        vapid_private_key=None,
        vapid_email=None,
    ):
        """
        Sends Web Push notifications to one or more browser subscriptions.

        Configuration is pulled from the App instance if not provided
        explicitly through the method parameters.

        :type subscriptions: List
        :param subscriptions: List of subscription dicts with endpoint,
        p256dh, and auth keys.
        :type message: Dictionary/String
        :param message: Notification payload.
        :type vapid_private_key: String
        :param vapid_private_key: VAPID private key (defaults to app.vapid_key).
        :type vapid_email: String
        :param vapid_email: VAPID contact email (defaults to app.vapid_email).
        :rtype: Dictionary
        :return: Result with success status and sent endpoints.
        """

        return self._web_push_handler.send_to_subscriptions(
            subscriptions=subscriptions,
            message=message,
            app=self.app,
            vapid_private_key=vapid_private_key,
            vapid_email=vapid_email,
        )


class _StandaloneAPNHandler(apn.APNHandler):
    """Standalone APN handler for use without a State owner."""

    def __init__(self, logger):
        self.owner = None
        self.name = "apn"
        self.logger = logger
        self.subs = {}


class _StandaloneSMTPHandler(smtp.SMTPHandler):
    """Standalone SMTP handler for use without a State owner."""

    def __init__(self, logger):
        self.owner = None
        self.name = "smtp"
        self.logger = logger
        self.subs = {}


class _StandaloneWebHandler(web.WebHandler):
    """Standalone Web handler for use without a State owner."""

    def __init__(self, logger):
        self.owner = None
        self.name = "web"
        self.logger = logger
        self.subs = {}


class _StandaloneWebPushHandler(web_push.WebPushHandler):
    """Standalone Web Push handler for use without a State owner."""

    def __init__(self, logger):
        self.owner = None
        self.name = "web_push"
        self.logger = logger
        self.subs = {}


class _NullLogger(object):
    """Null logger that discards all log messages."""

    def debug(self, *args, **kwargs):
        pass

    def info(self, *args, **kwargs):
        pass

    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass
