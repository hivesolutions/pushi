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

import uuid
import hashlib

import appier

from . import base


class App(base.PushiBase):
    """
    Core application model representing a Pushi tenant/application instance.

    This is the root entity in the Pushi multi-tenant architecture. Each App
    represents a distinct application with its own credentials, configuration,
    and isolated data. All other models (Subscription, Event, APN, Web, WebPush)
    are scoped to an App via the `instance` field inherited from PushiBase.

    Cardinality:
        - One App owns many Subscriptions, Events, Associations, APNs, Webs, WebPushs.
        - App is the root of the data hierarchy; deleting an App orphans related data.
        - The `ident` field is used as the `instance` value in child models.

    Credentials:
        - `ident`: Application identifier, used for internal routing and scoping.
        - `key`: Public API key for authenticating client requests.
        - `secret`: Private key for secure server-to-server operations and signing.
        - All credentials are auto-generated as SHA256 hashes of UUIDs on creation.

    Push notification configuration:
        - APN (Apple Push Notifications): Requires `apn_key`, `apn_cer`, and
          `apn_sandbox` flag for iOS push notifications.
        - Web Push (W3C Push API): Requires `vapid_key` and `vapid_email` for
          browser push notifications.

    Lifecycle:
        - On create: Auto-generates `ident`, `key`, and `secret` credentials.
        - The `instance` field is set to `ident` for self-referential scoping.
        - Credentials are immutable after creation for security.

    Cautions:
        - Credential exposure: The `key` and `secret` fields are marked `safe=True`
          but should still be protected; avoid logging or exposing in responses.
        - No cascade delete: Deleting an App does not automatically clean up
          related Subscriptions, Events, etc. Implement cleanup if required.
        - APN certificate management: The `apn_key` and `apn_cer` must be kept
          in sync with Apple Developer portal; expired certs cause delivery failures.
        - Unique names: App names must be unique within the system.

    Related models:
        - Subscription, Association, PushiEvent, APN, Web, WebPush: All scoped to App.
        - PushiBase: Provides the `instance` field and multi-tenancy behavior.
    """

    name = appier.field(
        index=True,
        default=True,
        observations="""The human readable name of the Pushi application,
        used for identification and display purposes""",
    )
    """
    Human-readable application name for identification and display.

    :type: str
    """

    ident = appier.field(
        index=True,
        safe=True,
        immutable=True,
        observations="""The unique identifier of the application, automatically
        generated as a SHA256 hash of a UUID on creation""",
    )
    """
    Unique app identifier (SHA256 hash), auto-generated on creation.
    Used as the `instance` value to scope all child models.

    :type: str
    """

    key = appier.field(
        index=True,
        safe=True,
        immutable=True,
        observations="""The API key used for authenticating requests to the
        Pushi system, automatically generated as a SHA256 hash on creation""",
    )
    """
    Public API key for client authentication, auto-generated on creation.
    Used by clients to identify themselves when connecting.

    :type: str
    """

    secret = appier.field(
        index=True,
        safe=True,
        immutable=True,
        observations="""The secret key used for secure operations and signing,
        automatically generated as a SHA256 hash on creation""",
    )
    """
    Private secret for server-to-server operations and signing.
    Should never be exposed to clients; auto-generated on creation.

    :type: str
    """

    apn_sandbox = appier.field(
        type=bool,
        description="APN Sandbox",
        observations="""Indicates if the APN context is sandbox or
        production related, should be in sync with Apple Development configuration""",
    )
    """
    Flag indicating sandbox (True) or production (False) APN environment.
    Must match the environment of registered device tokens.

    :type: bool
    """

    apn_key = appier.field(
        meta="longtext",
        description="APN Key",
        observations="""The private key in PEM format to be used
        in messages to be sent using APN (Apple Push Notifications)""",
    )
    """
    PEM-formatted private key for Apple Push Notification authentication.
    Obtained from Apple Developer portal; must match apn_cer.

    :type: str
    """

    apn_cer = appier.field(
        meta="longtext",
        description="APN Cer",
        observations="""The certificate in PEM format to be used
        in messages to be sent using APN (Apple Push Notifications)""",
    )
    """
    PEM-formatted certificate for Apple Push Notification authentication.
    Obtained from Apple Developer portal; must match apn_key.

    :type: str
    """

    vapid_key = appier.field(
        meta="longtext",
        description="VAPID Private Key",
        observations="""The private key in PEM or base64url format to be used
        for VAPID authentication in Web Push notifications (RFC 8292)""",
    )
    """
    Private key (PEM or base64url) for VAPID Web Push authentication.
    Used to sign JWT tokens per RFC 8292.

    :type: str
    """

    vapid_email = appier.field(
        description="VAPID Email",
        observations="""The contact email for VAPID claims (usually mailto: format),
        used as the subject in VAPID JWT tokens for Web Push""",
    )
    """
    Contact email (mailto: format) for VAPID JWT subject claim.
    Used by push services to contact the application operator.

    :type: str
    """

    smtp_url = appier.field(
        description="SMTP URL",
        observations="""SMTP URL for email notifications in the format
        smtp://user:password@host:port?sender=from@example.com or
        smtps://... for STARTTLS. Falls back to global SMTP_URL if not set.""",
    )
    """
    SMTP connection URL for sending email notifications.
    Format: smtp://[user:password@]host[:port][?sender=email]
    Use smtps:// scheme for STARTTLS connections.

    :type: str
    """

    @classmethod
    def validate(cls):
        return super(App, cls).validate() + [
            appier.not_null("name"),
            appier.not_empty("name"),
            appier.not_duplicate("name", cls._name()),
        ]

    @classmethod
    def list_names(cls):
        return ["name", "ident", "apn_sandbox"]

    def pre_create(self):
        base.PushiBase.pre_create(self)

        ident = appier.legacy.bytes(str(uuid.uuid4()))
        key = appier.legacy.bytes(str((uuid.uuid4())))
        secret = appier.legacy.bytes(str(uuid.uuid4()))

        self.ident = hashlib.sha256(ident).hexdigest()
        self.key = hashlib.sha256(key).hexdigest()
        self.secret = hashlib.sha256(secret).hexdigest()

        self.instance = self.ident

    @appier.operation(
        name="Generate VAPID",
        description="""Generates a new VAPID key pair for Web Push notifications,
        setting the private key on this application""",
        parameters=(("Email", "email", str, ""),),
    )
    def generate_vapid_s(self, email=""):
        # tries to import the py_vapid library which is
        # required for generating the VAPID key pair
        try:
            import py_vapid
        except ImportError:
            raise appier.OperationalError(
                message="py_vapid library not available, required for VAPID generation"
            )

        # generates a new VAPID key pair using the py_vapid
        # library and extracts the private key
        vapid = py_vapid.Vapid()
        vapid.generate_keys()

        # sets the private key on the model in PEM format
        # and optionally sets the email if provided
        self.vapid_key = vapid.private_pem().decode("utf-8")
        if email:
            self.vapid_email = email

        # saves the model with the new VAPID credentials
        self.save()
