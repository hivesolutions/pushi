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

import time

import appier

import pushi


class HealthController(appier.Controller):
    """
    Controller for health check endpoints.

    Provides endpoints for monitoring the health status of the Pushi
    system, including database connectivity, WebSocket server status,
    and handler health.
    """

    @appier.route("/health", "GET")
    def health(self):
        """
        Simple health check endpoint for load balancers.

        Returns a basic health status without detailed checks.
        This endpoint is designed to be fast and lightweight
        for frequent polling by load balancers and monitoring tools.

        :rtype: Dictionary
        :return: Dictionary containing basic health status.
        """

        return dict(status="ok", service="pushi", version=self.owner._version())

    @appier.route("/health/detailed", "GET")
    def health_detailed(self):
        """
        Detailed health check endpoint for debugging and monitoring.

        Performs comprehensive health checks on all system components:
        - Database connectivity (MongoDB)
        - WebSocket server status
        - Handler health (APN, Web, WebPush)

        :rtype: Dictionary
        :return: Dictionary containing detailed health status for all components.
        """

        # initializes the response structure with basic info
        response = dict(
            status="ok",
            service="pushi",
            version=self.owner._version(),
            timestamp=time.time(),
            checks=dict(),
        )

        # tracks overall health status
        is_healthy = True

        # performs the database health check
        db_check = self._check_database()
        response["checks"]["database"] = db_check
        if not db_check["status"] == "ok":
            is_healthy = False

        # performs the WebSocket server health check
        ws_check = self._check_websocket_server()
        response["checks"]["websocket"] = ws_check
        if not ws_check["status"] == "ok":
            is_healthy = False

        # performs the handlers health check
        handlers_check = self._check_handlers()
        response["checks"]["handlers"] = handlers_check
        if not handlers_check["status"] == "ok":
            is_healthy = False

        # updates the overall status based on component checks
        if not is_healthy:
            response["status"] = "degraded"

        return response

    @appier.route("/health/live", "GET")
    def health_live(self):
        """
        Kubernetes liveness probe endpoint.

        Returns success if the application is running and able
        to handle requests. This is a minimal check that only
        verifies the application process is alive.

        :rtype: Dictionary
        :return: Dictionary containing liveness status.
        """

        return dict(status="ok")

    @appier.route("/health/ready", "GET")
    def health_ready(self):
        """
        Kubernetes readiness probe endpoint.

        Returns success only if the application is fully ready
        to accept traffic, including database connectivity and
        WebSocket server availability.

        :rtype: Dictionary
        :return: Dictionary containing readiness status.
        """

        # checks if database is accessible
        db_check = self._check_database()
        if not db_check["status"] == "ok":
            raise appier.OperationalError(
                message="Database not ready: %s" % db_check.get("error", "unknown"),
                code=503,
            )

        # checks if WebSocket server is running
        ws_check = self._check_websocket_server()
        if not ws_check["status"] == "ok":
            raise appier.OperationalError(
                message="WebSocket server not ready: %s"
                % ws_check.get("error", "unknown"),
                code=503,
            )

        return dict(status="ok", ready=True)

    def _check_database(self):
        """
        Checks the database connectivity by performing a simple query.

        :rtype: Dictionary
        :return: Dictionary containing database health status.
        """

        start_time = time.time()

        try:
            # performs a simple count query to verify database connectivity
            # this is a lightweight operation that verifies the connection
            count = pushi.App.count()
            latency_ms = (time.time() - start_time) * 1000

            return dict(
                status="ok",
                latency_ms=round(latency_ms, 2),
                app_count=count,
            )
        except Exception as exception:
            latency_ms = (time.time() - start_time) * 1000

            return dict(
                status="error",
                error=str(exception),
                latency_ms=round(latency_ms, 2),
            )

    def _check_websocket_server(self):
        """
        Checks the WebSocket server status.

        :rtype: Dictionary
        :return: Dictionary containing WebSocket server health status.
        """

        try:
            # retrieves the state from the application
            state = getattr(self.owner, "state", None)
            if state == None:
                return dict(
                    status="warning",
                    error="State not initialized",
                )

            # retrieves the server from the state
            server = getattr(state, "server", None)
            if server == None:
                return dict(
                    status="warning",
                    error="WebSocket server not initialized",
                )

            # retrieves server statistics
            server_info = server.info_dict() if hasattr(server, "info_dict") else {}
            connection_count = len(getattr(server, "sockets", {}))
            message_count = getattr(server, "count", 0)

            return dict(
                status="ok",
                connections=connection_count,
                messages_sent=message_count,
                info=server_info,
            )
        except Exception as exception:
            return dict(
                status="error",
                error=str(exception),
            )

    def _check_handlers(self):
        """
        Checks the health of all registered handlers.

        :rtype: Dictionary
        :return: Dictionary containing handler health status.
        """

        try:
            # retrieves the state from the application
            state = getattr(self.owner, "state", None)
            if state == None:
                return dict(
                    status="warning",
                    error="State not initialized",
                )

            # retrieves the handlers list from state
            handlers = getattr(state, "handlers", [])
            if not handlers:
                return dict(
                    status="warning",
                    error="No handlers registered",
                    handlers=[],
                )

            # checks each handler
            handler_statuses = []
            all_ok = True

            for handler in handlers:
                handler_status = self._check_handler(handler)
                handler_statuses.append(handler_status)
                if not handler_status["status"] == "ok":
                    all_ok = False

            return dict(
                status="ok" if all_ok else "degraded",
                handlers=handler_statuses,
            )
        except Exception as exception:
            return dict(
                status="error",
                error=str(exception),
                handlers=[],
            )

    def _check_handler(self, handler):
        """
        Checks the health of a single handler.

        :type handler: Handler
        :param handler: The handler instance to check.
        :rtype: Dictionary
        :return: Dictionary containing handler health status.
        """

        try:
            handler_name = getattr(handler, "name", handler.__class__.__name__)

            # builds handler-specific stats based on handler type
            stats = dict()

            # checks for subscription count if available (WebPushHandler, APNHandler, etc.)
            # note: we avoid hasattr() because in Python 2 it catches all exceptions,
            # not just AttributeError, which would swallow errors from property access
            try:
                subs = handler.subs
                total_subscriptions = sum(
                    sum(len(events) for events in app_subs.values())
                    for app_subs in subs.values()
                )
                stats["subscription_count"] = total_subscriptions
                stats["app_count"] = len(subs)
            except AttributeError:
                pass

            # checks for tokens if available (APNHandler)
            try:
                tokens = handler.tokens
                total_tokens = sum(
                    sum(len(events) for events in app_tokens.values())
                    for app_tokens in tokens.values()
                )
                stats["token_count"] = total_tokens
            except AttributeError:
                pass

            return dict(
                name=handler_name,
                status="ok",
                stats=stats,
            )
        except Exception as exception:
            handler_name = getattr(handler, "name", "unknown")
            return dict(
                name=handler_name,
                status="error",
                error=str(exception),
            )
