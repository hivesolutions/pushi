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
import email.mime.text

import appier

import netius
import netius.clients

import pushi

from . import handler


class MailHandler(handler.Handler):
    """
    Event handler to be used for email (SMTP) based notifications.

    This handler provides the abstraction for sending email
    notifications when events are triggered on subscribed channels.

    Notification here will be sent using the netius SMTP client
    to deliver emails to subscribed addresses.

    The handler requires SMTP configuration via environment variables
    to function. If SMTP_HOST is not configured, the handler will
    gracefully skip sending emails.

    :see: https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol
    """

    def __init__(self, owner):
        handler.Handler.__init__(self, owner, name="mail")
        self.subs = {}

    def send(self, app_id, event, json_d, invalid={}):
        # retrieves the SMTP configuration from environment variables using
        # the appier configuration system for proper defaults
        smtp_host = appier.conf("SMTP_HOST", None)
        smtp_port = appier.conf("SMTP_PORT", 25, cast=int)
        smtp_user = appier.conf("SMTP_USER", None)
        smtp_password = appier.conf("SMTP_PASSWORD", None)
        smtp_starttls = appier.conf("SMTP_STARTTLS", False, cast=bool)
        smtp_sender = appier.conf("SMTP_SENDER", None)

        # in case the SMTP host is not configured skips the sending operation
        # as there's no way to send emails without a valid host
        if not smtp_host:
            return

        # in case the SMTP sender is not configured skips the sending operation
        # as a valid sender address is required for email delivery
        if not smtp_sender:
            return

        # retrieves the reference to the app structure associated with the
        # id for which the message is being send
        app = self.owner.get_app(app_id=app_id)

        # retrieves the app key for the retrieved app by unpacking the current
        # app structure into the appropriate values
        app_key = app.key

        # saves the original event name for the received event, so that it may
        # be used latter for debugging/log purposes
        root_event = event

        # resolves the complete set of (extra) channels for the provided
        # event assuming that it may be associated with alias, then creates
        # the complete list of event containing also the "extra" events
        extra = self.owner.get_channels(app_key, event)
        events = [event] + extra

        # retrieves the complete set of subscriptions for the current mail
        # infra-structure to be able to resolve the appropriate emails
        subs = self.subs.get(app_id, {})

        # creates the initial list of emails to be notified and then populates
        # the list with the various emails associated with the complete set of
        # resolved events, note that a set is created at the end so that one
        # email gets notified only once (no double notifications)
        emails = []
        for event in events:
            _emails = subs.get(event, [])
            emails.extend(_emails)
        emails = set(emails)
        count = len(emails)

        # prints a logging message about the various (mail) subscriptions
        # that were found for the event that was triggered
        self.logger.debug(
            "Found %d Mail subscription(s) for '%s'" % (count, root_event)
        )

        # in case there are no emails to notify returns immediately
        # as there's no need to build the email content
        if not emails:
            return

        # extracts the event data from the JSON dictionary, this will be
        # used to build the email content
        data = json_d.get("data", None)
        channel = json_d.get("channel", root_event)
        event_name = json_d.get("event", root_event)

        # tries to extract custom subject and body from the JSON dictionary
        # allowing the caller to override the default email format
        custom_subject = json_d.get("subject", None)
        custom_body = json_d.get("body", None)

        # builds the subject line for the email, using custom subject if
        # provided or falling back to the default format
        if custom_subject:
            subject = custom_subject
        else:
            subject = "[Pushi] %s" % event_name

        # builds the body content for the email, using custom body if
        # provided or falling back to the default format with event details
        if custom_body:
            body = custom_body
        else:
            # serializes the data to JSON for inclusion in the email body
            # if the data is not already a string
            if data and not isinstance(data, str):
                data_str = json.dumps(data, indent=2)
            else:
                data_str = data or "(no data)"

            body = """Event Notification
==================

Channel: %s
Event: %s

Data:
%s
""" % (
                channel,
                event_name,
                data_str,
            )

        # iterates over the complete set of emails that are going to
        # be notified about the message, each of them is going to
        # received an email with the event data
        for target_email in emails:
            # in case the current email is present in the current
            # map of invalid items must skip iteration as the message
            # has probably already been sent to the target email
            if target_email in invalid:
                continue

            # prints a debug message about the mail message that
            # is going to be sent (includes email address)
            self.logger.debug("Sending email to '%s'" % target_email)

            # builds the MIME message for the email using the plain text
            # content type for simple text emails
            mime = email.mime.text.MIMEText(body)
            mime["Subject"] = subject
            mime["From"] = smtp_sender
            mime["To"] = target_email
            contents = mime.as_string()

            # creates the callback function that is going to be used when
            # the SMTP connection is closed after sending the email
            def on_close(connection=None):
                netius.compat_loop(loop).stop()

            # creates the callback function that handles any exceptions
            # that may occur during the SMTP sending process
            def on_exception(connection=None, exception=None):
                self.logger.warning(
                    "Failed to send email to '%s': %s"
                    % (target_email, appier.legacy.UNICODE(exception))
                )
                netius.compat_loop(loop).stop()

            # creates the SMTP client and sends the message using the
            # configured SMTP settings, the auto_close flag ensures the
            # client closes after the message is sent
            smtp_client = netius.clients.SMTPClient(auto_close=True)
            connection = smtp_client.message(
                [smtp_sender],
                [target_email],
                contents,
                host=smtp_host,
                port=smtp_port,
                username=smtp_user,
                password=smtp_password,
                stls=smtp_starttls,
            )

            # binds the close and exception events to the connection
            # to handle the completion of the send operation
            if connection:
                connection.bind("close", on_close)
                connection.bind("exception", on_exception)

                # retrieves the event loop and runs it until the email
                # is sent and the connection is closed
                loop = smtp_client.get_loop()
                loop.run_forever()

            # adds the current email to the list of invalid items for
            # the current message sending stream
            invalid[target_email] = True

    def load(self):
        subs = pushi.Mail.find()
        for sub in subs:
            app_id = sub.app_id
            target_email = sub.email
            event = sub.event
            self.add(app_id, target_email, event)

    def add(self, app_id, email, event):
        events = self.subs.get(app_id, {})
        emails = events.get(event, [])
        emails.append(email)
        events[event] = emails
        self.subs[app_id] = events

    def remove(self, app_id, email, event):
        events = self.subs.get(app_id, {})
        emails = events.get(event, [])
        if email in emails:
            emails.remove(email)

    def subscriptions(self, email=None, event=None):
        filter = dict()
        if email:
            filter["email"] = email
        if event:
            filter["event"] = event
        subscriptions = pushi.Mail.find(map=True, **filter)
        return dict(subscriptions=subscriptions)

    def subscribe(self, mail, auth=None, unsubscribe=True):
        self.logger.debug("Subscribing '%s' for '%s'" % (mail.email, mail.event))

        is_private = (
            mail.event.startswith("private-")
            or mail.event.startswith("presence-")
            or mail.event.startswith("peer-")
            or mail.event.startswith("personal-")
        )

        is_private and self.owner.verify(mail.app_key, mail.email, mail.event, auth)
        unsubscribe and self.unsubscribe(mail.email, force=False)

        exists = pushi.Mail.exists(email=mail.email, event=mail.event)
        if exists:
            mail = exists
        else:
            mail.save()

        self.logger.debug("Subscribed '%s' for '%s'" % (mail.email, mail.event))

        return mail

    def unsubscribe(self, email, event=None, force=True):
        self.logger.debug("Unsubscribing '%s' from '%s'" % (email, event or "*"))

        kwargs = dict(email=email, raise_e=force)
        if event:
            kwargs["event"] = event

        mail = pushi.Mail.get(**kwargs)
        if not mail:
            return None

        mail.delete()

        self.logger.debug("Unsubscribed '%s' for '%s'" % (email, event or "*"))

        return mail

    def unsubscribes(self, email, event=None):
        kwargs = dict(email=email)
        if event:
            kwargs["event"] = event

        mails = pushi.Mail.find(**kwargs)
        for mail in mails:
            mail.delete()

        return mails
