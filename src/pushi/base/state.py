#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (c) 2008-2018 Hive Solutions Lda.
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

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import os
import sys
import time
import json
import hmac
import uuid
import copy
import hashlib
import datetime
import threading

base_dir = os.path.normpath((os.path.dirname(__file__) or ".") + "/../..")
if not base_dir in sys.path: sys.path.insert(0, base_dir)

import pushi
import appier

from pushi.base import apn
from pushi.base import web

class AppState(object):
    """
    The state object that defined the various state variables
    for an app registered in the system. There should be one
    of this objects per each application loaded.
    """

    def __init__(self, app_id, app_key):
        self.app_id = app_id
        self.app_key = app_key
        self.alias = {}
        self.alias_i = {}
        self.socket_channels = {}
        self.channel_sockets = {}
        self.channel_info = {}
        self.channel_socket_data = {}

class State(appier.Mongo):
    """
    Main logic of the pushi infra-structure, this class
    should contain the main structures and operations that
    control a system for push notifications.

    It should run in an asynchronous nonblocking fashion to
    avoid the typical locking related problems (eg: dead locks)
    and at the same time handle the c10k problem.

    The structure of the system is based on the encapsulation
    of both the (async) server and the web based app that handles
    the http based requests (rest api).
    """

    def __init__(self):
        appier.Mongo.__init__(self)
        self.app = None
        self.server = None
        self.apn_handler = None
        self.handlers = []
        self.app_id_state = {}
        self.app_key_state = {}

    def load(self, app, server):
        # sets the references to both the app and the server in the
        # current instance, this values are going to be used latter
        self.app = app
        self.server = server

        # "moves" the (in memory) logging handlers of the app to the
        # server so that they share a common logging infrastructure
        handlers = self.app.handlers
        level = self.app.level
        self.server.handlers = handlers
        self.server.level = level

        # registers for the various base events in the server so that
        # it's able to properly update the current state of the application
        # to the new state (according to the operation)
        self.server.bind("connect", self.connect)
        self.server.bind("disconnect", self.disconnect)
        self.server.bind("subscribe", self.subscribe)
        self.server.bind("unsubscribe", self.unsubscribe)
        self.server.bind("validate", self.validate)

        # retrieves the various environment variable values that are going
        # to be used in the starting of both the app server and the proper
        # pushi server (most of the values have default values)
        APP_SERVER = os.environ.get("APP_SERVER", "netius")
        APP_HOST = os.environ.get("APP_HOST", "127.0.0.1")
        APP_PORT = int(os.environ.get("APP_PORT", "8080"))
        APP_SSL = bool(int(os.environ.get("APP_SSL", "0")))
        APP_SSL_KEY = os.environ.get("APP_SSL_KEY", None)
        APP_SSL_CER = os.environ.get("APP_SSL_CER", None)
        SERVER_HOST = os.environ.get("SERVER_HOST", "127.0.0.1")
        SERVER_PORT = int(os.environ.get("SERVER_PORT", "9090"))
        SERVER_SSL = bool(int(os.environ.get("SERVER_SSL", "0")))
        SERVER_SSL_KEY = os.environ.get("SERVER_SSL_KEY", None)
        SERVER_SSL_CER = os.environ.get("SERVER_SSL_CER", None)

        # creates the named argument for both the app server and the proper
        # pushi server so that they are correctly initialized and bound to
        # the proper ports (infinite loop)
        app_kwargs = dict(
            server = APP_SERVER,
            host = APP_HOST,
            port = APP_PORT,
            ssl = APP_SSL,
            key_file = APP_SSL_KEY,
            cer_file = APP_SSL_CER
        )
        server_kwargs = dict(
            host = SERVER_HOST,
            port = SERVER_PORT,
            ssl = SERVER_SSL,
            key_file = SERVER_SSL_KEY,
            cer_file = SERVER_SSL_CER
        )

        # creates the threads that will be used as containers for the app and
        # the pushi server and then starts them with the proper arguments
        threading.Thread(target = self.app.serve, kwargs = app_kwargs).start()
        threading.Thread(target = self.server.serve, kwargs = server_kwargs).start()

        # starts the loading process of the various (extra handlers) that are
        # going to be used in the pushi infra-structure (eg: apn, gcm, etc.)
        self.load_handlers()

        # loads the various alias relations for the current infra-structure so
        # that the personal channels are able to correctly work
        self.load_alias()

    def load_handlers(self):
        self.apn_handler = apn.APNHandler(self)
        self.web_handler = web.WebHandler(self)

        self.apn_handler.load()
        self.web_handler.load()

        self.handlers.append(self.apn_handler)
        self.handlers.append(self.web_handler)

    def load_alias(self):
        """
        Loads the complete set of alias (channels that represent) the
        same for the current context, this may be used for a variety
        of reasons including the personal channels.
        """

        # retrieves the complete set of subscriptions from the currently
        # associated data source reference and then uses them to create
        # the complete personal to proper channel relation
        subs = pushi.Subscription.find()
        for sub in subs:
            app_id = sub.app_id
            user_id = sub.user_id
            event = sub.event
            app_key = self.app_id_to_app_key(app_id)
            self.add_alias(app_key, "personal-" + user_id, event)

    def add_alias(self, app_key, channel, alias):
        self.app.logger.debug(
            "Adding '%s' into '%s' for app key '%s'" %
            (alias, channel, app_key)
        )

        state = self.get_state(app_key = app_key)
        alias_l = state.alias.get(channel, [])
        if alias in alias_l: return

        alias_l.append(alias)
        state.alias[channel] = alias_l

        alias_l = state.alias_i.get(alias, [])
        if channel in alias_l: return

        alias_l.append(channel)
        state.alias_i[alias] = alias_l

    def remove_alias(self, app_key, channel, alias):
        self.app.logger.debug(
            "Removing '%s' from '%s' for app key '%s'" %
            (alias, channel, app_key)
        )

        state = self.get_state(app_key = app_key)
        alias_l = state.alias.get(channel, [])
        if not alias in alias_l: return

        alias_l.remove(alias)
        if not alias_l: del state.alias[channel]

        alias_l = state.alias_i.get(alias, [])
        if not channel in alias_l: return

        alias_l.remove(channel)
        if not alias_l: del state.alias_i[alias]

    def connect(self, connection, app_key, socket_id):
        pass

    def disconnect(self, connection, app_key, socket_id):
        # in case no app key or socket id is defined must return
        # immediately because it's not possible to perform the
        # disconnect operation in such conditions, possible a non
        # established connection is attempting to disconnect
        if not app_key: return
        if not socket_id: return

        # verifies if there's an app value available for the app key
        # in case there's not, returns immediately, as it's not possible
        # to disconnect a connection without an associated/valid app
        if not self.has_app(app_key = app_key): return

        # retrieves the current state of the app using the app key and
        # then uses it to retrieve the complete set of channels that the
        # socket is subscribed and then unsubscribe it from them then
        # removes the reference of the socket in the socket channels map
        state = self.get_state(app_key = app_key)
        channels = state.socket_channels.get(socket_id, [])
        channels = copy.copy(channels)
        for channel in channels: self.unsubscribe(connection, app_key, socket_id, channel)
        if socket_id in state.socket_channels: del state.socket_channels[socket_id]

    def subscribe(
        self,
        connection,
        app_key,
        socket_id,
        channel,
        auth = None,
        channel_data = None,
        force = False
    ):
        # checks if the the channel to be registered is considered private
        # (either private, presence or peer) and in case it's private verifies
        # if the correct credentials (including auth token) are valid
        is_private = channel.startswith("private-") or\
            channel.startswith("presence-") or channel.startswith("peer-") or\
            channel.startswith("personal-")
        if is_private and not force: self.verify(app_key, socket_id, channel, auth)

        # verifies if the current channel is of type personal and in
        # case it's retrieves it's alias (channels) and subscribes to
        # all of them (as expected), then return immediately
        is_personal = channel.startswith("personal-")
        if is_personal:
            channels = self.get_alias(app_key, channel)
            for channel in channels:
                self.subscribe(
                    connection,
                    app_key,
                    socket_id,
                    channel,
                    auth = auth,
                    channel_data = channel_data,
                    force = True
                )
            return

        # verifies if the channel is of type presence (prefix based
        # verification) and in case it's not invalidate the channel
        # data as channel data is not valid
        is_presence = channel.startswith("presence-")
        if not is_presence: channel_data = None

        # verifies if the current connection (by socket id) is already
        # registered to the channel and in case it's unsubscribes the
        # connection from it (avoids duplicated registration)
        is_subscribed = self.is_subscribed(app_key, socket_id, channel)
        if is_subscribed: self.unsubscribe(connection, app_key, socket_id, channel)

        # retrieves the global state structure for the provided api key
        # and also creates the tuple that encapsulates both the channel
        # and the socket id (unique identification)
        state = self.get_state(app_key = app_key)
        channel_socket = (channel, socket_id)

        # retrieves the complete set of channels for the socket id and
        # adds the current channel to it (subscription) then updates the
        # association between the socket id and the channels
        channels = state.socket_channels.get(socket_id, [])
        subscribed = channel in channels
        if subscribed: raise RuntimeError("Channel already subscribed")
        channels.append(channel)
        state.socket_channels[socket_id] = channels

        # retrieves the complete set of sockets for the channels (inverted)
        # association and adds the current socket id to the list then
        # re-updates the inverted map with the sockets list
        sockets = state.channel_sockets.get(channel, [])
        subscribed = socket_id in sockets
        if subscribed: raise RuntimeError("Socket already subscribed")
        sockets.append(socket_id)
        state.channel_sockets[channel] = sockets

        # in case there's no channel data to be used to change
        # metadata and in additional processing must return
        # immediately as there's nothing else remaining to be
        # done in the subscription process
        if not channel_data: return

        # unpacks the information from the channel data, defaulting
        # some of the values to their fallback values
        user_id = channel_data["user_id"]
        is_peer = channel_data.get("peer", False)

        # "saves" the channel data for the channel socket tuple in the
        # appropriate data structure to be used latter
        state.channel_socket_data[channel_socket] = channel_data

        # retrieves the channel info for the channel that is going to be
        # subscribed and "unpacks" the complete state information from it
        # so that it may be used and updated
        info = state.channel_info.get(channel, {})
        users = info.get("users", {})
        members = info.get("members", {})
        conns = info.get("conns", [])
        user_count = info.get("user_count", 0)

        # adds the current connection to the list of connection for the
        # the current channel (state information update)
        conns.append(connection)

        # retrieves the list of connection to the current user id that is
        # going to be used and adds the current connection, then re-updates
        # the user connections list and the channel data
        user_conns = users.get(user_id, [])
        user_conns.append(connection)
        users[user_id] = user_conns
        members[user_id] = channel_data

        # verifies if the current subscription is going to create a new user
        # subscription (that must be logger) this is the case if the number
        # of connection currently subscribed is one
        is_new = len(user_conns) == 1
        if is_new: user_count += 1

        # updates the info dictionary with the new complete set of values for
        # the channel information
        info["users"] = users
        info["members"] = members
        info["conns"] = conns
        info["user_count"] = user_count
        state.channel_info[channel] = info

        # subscribes all of the peer channels associated with the current
        # presence channel that is being subscribed, this may represent some
        # overhead but provides peer to peer communication
        is_peer and self.subscribe_peer_all(app_key, connection, channel)

        # in case the connection does not represent a new user logging in must
        # return immediately, because there's nothing remaining to be done
        if not is_new: return

        # creates the json dictionary containing the event to be sent to all
        # of the socket in the channel indicating the presence change for the
        # "new" user that has just logged in (member added)
        json_d = dict(
            event = "pusher:member_added",
            member = json.dumps(channel_data),
            channel = channel
        )

        # iterates over the complete set of connections currently subscribed
        # to the channel, in order to be notify them about the member added
        for _connection in conns:
            if _connection == connection: continue
            _connection.send_pushi(json_d)

            # in case the connection is not of type peer there's nothing
            # else to be done related with the other connections
            if not is_peer: continue

            # retrieves the socket id of the current connection in iteration
            # and uses it to construct the channel socket id tuple to try to
            # retrieve the channel data for the socket in case it does not
            # exists skips the current step, no need to subscribe to chat
            # specific channel (because there's no channel data)
            _socket_id = _connection.socket_id
            _channel_socket = (channel, _socket_id)
            _channel_data = state.channel_socket_data.get(_channel_socket)
            if not _channel_data: continue

            # retrieves the user id of the current channel data for the user
            # in iteration and the uses this value to subscribe it for the
            # peer channel with the current member (that was just added)
            _user_id = _channel_data["user_id"]
            self.subscribe_peer(
                app_key, _connection, channel, user_id, _user_id
            )

    def unsubscribe(self, connection, app_key, socket_id, channel):
        # checks if the current channel is a private one and in case
        # it's runs the unsubscription operation for all of the alias
        # channels associated with this personal one
        is_personal = channel.startswith("personal-")
        if is_personal:
            channels = self.get_alias(app_key, channel)
            for channel in channels:
                self.unsubscribe(
                    connection,
                    app_key,
                    socket_id,
                    channel
                )
            return

        # runs the validation process for the subscription to the
        # current channel, meaning that in case the current socket
        # is not subscribed to the channel an exception will be raised
        self.validate(connection, app_key, socket_id, channel)

        # uses the provided app key to retrieve the state of the
        # app and then creates the channel socket tuple that is
        # going to be used for unique identification
        state = self.get_state(app_key = app_key)
        channel_socket = (channel, socket_id)

        # retrieves the list of channels for which the provided socket
        # id is currently subscribed and removes the current channel
        # from that list in case it exists there
        channels = state.socket_channels.get(socket_id, [])
        if channel in channels: channels.remove(channel)

        # retrieves the list of sockets that are subscribed to the defined
        # channel and removes the current socket from it
        sockets = state.channel_sockets.get(channel, [])
        if socket_id in sockets: sockets.remove(socket_id)

        # tries to retrieve the channel data for the channel socket
        # tuple in case there's none available there's nothing else
        # remaining to be done in the unsubscribe process
        channel_data = state.channel_socket_data.get(channel_socket)
        if not channel_data: return

        # deletes the channel socket tuple reference from the channel
        # socket data list, no longer going to be required
        del state.channel_socket_data[channel_socket]

        # retrieves both the information on the user id associated with
        # the channel data and the is peer (channel) boolean flag
        user_id = channel_data["user_id"]
        is_peer = channel_data.get("peer", False)

        # gather information on the channel from the global state object
        # this would include the amount of users the members, current
        # connections and more
        info = state.channel_info.get(channel, {})
        users = info.get("users", {})
        members = info.get("members", {})
        conns = info.get("conns", [])
        user_count = info.get("user_count", 0)

        # removes the current connection from the list of connection currently
        # active for the channel, because it's no longer available
        conns.remove(connection)

        # retrieves the currently active connections registered under the user id
        # of the connection to be unregistered then removes the current connection
        # from the list of connections and re-sets the connections list
        user_conns = users.get(user_id, [])
        user_conns.remove(connection)
        users[user_id] = user_conns

        # verifies if the current connection is old, a connection is considered
        # old when no more connections exist for a certain user id in the channel
        # for this situations additional housekeeping must be performed
        is_old = len(user_conns) == 0
        if is_old: del users[user_id]; del members[user_id]; user_count -= 1

        # updates the various attributes of the channel information structure
        # so that it remains updated according to the unsubscribe operation
        info["users"] = users
        info["members"] = members
        info["conns"] = conns
        info["user_count"] = user_count
        state.channel_info[channel] = info

        # unsubscribes from the complete set of peer channels associated with
        # the current presence channel, this is an expensive operation controlled
        # by the peer flat that may be set in the channel data structure
        is_peer and self.unsubscribe_peer_all(app_key, connection, channel)

        # verifies if the current connection is old in case it's not no operation
        # remain for the unsubscribe operation and so the function may return
        if not is_old: return

        # verifies if the current set of connection is empty (count is zero) so that
        # it's possible to know if the channel info for the channel should be removed
        is_empty = len(conns) == 0
        if is_empty: del state.channel_info[channel]

        # creates the map that is going to be used in the event to be sent to the set
        # sockets subscribed to the channel indicating that the member has been removed
        json_d = dict(
            event = "pusher:member_removed",
            member = json.dumps(channel_data),
            channel = channel
        )

        # iterates over the complete set of connections subscribed to the channel to notify
        # them about the member that has been removed from the channel
        for _connection in conns:
            # in case the current connection in iteration is the same as the
            # connection in subscription skips the current iteration otherwise
            # send the "member removed" message to the connection
            if _connection == connection: continue
            _connection.send_pushi(json_d)

            # in case the current subscription does not have the peer "mode" enabled
            # there's no need to continue as the rest of the iteration is dedicated
            # to the subscription of the peer channels
            if not is_peer: continue

            # retrieves the socket id of the current connection in iteration
            # and uses it to construct the channel socket id tuple to try to
            # retrieve the channel data for the socket in case it does not
            # exists skips the current step, no need to subscribe to chat
            # specific channel (because there's no channel data)
            _socket_id = _connection.socket_id
            _channel_socket = (channel, _socket_id)
            _channel_data = state.channel_socket_data.get(_channel_socket)
            if not _channel_data: continue

            # retrieves the user id for the connection in iteration for the current
            # channel and uses it to subscribe the connection to the peer channel
            _user_id = _channel_data["user_id"]
            self.unsubscribe_peer(
                app_key, _connection, channel, user_id, _user_id
            )

    def validate(self, connection, app_key, socket_id, channel):
        # verifies that the current socket is subscribed of eligible for
        # the provided channel and raises an exception in case it's not,
        # this provides a simple mechanism for security validation
        is_subscribed = self.is_subscribed(app_key, socket_id, channel)
        is_eligible = self.is_eligible(app_key, socket_id, channel)
        if not is_subscribed and not is_eligible:
            raise RuntimeError("Not subscribed/eligible to channel")

    def subscribe_peer_all(self, app_key, connection, channel):
        # creates the channel socket tuple with the channel name and the
        # socket identifier for the current connection
        state = self.get_state(app_key = app_key)
        channel_socket = (channel, connection.socket_id)

        # retrieves the channel data information for the current channel
        # socket and in case there's none returns immediately
        channel_data = state.channel_socket_data.get(channel_socket)
        if not channel_data: return

        # retrieves the user identifier from the channel data of the current
        # connection in the channel
        user_id = channel_data["user_id"]

        # uses the channel information to retrieve the list of currently
        # registered connections for the channel, these are going to be
        # used in the subscription iteration
        info = state.channel_info.get(channel, {})
        conns = info.get("conns", [])

        # creates the list that will hold the list of user identifier
        # that have already been visited so that no more that one peer
        # subscription is done by type
        visited = []

        # iterates over all the connections subscribed for the current channel
        # to be able to register for each of the peer channels
        for _connection in conns:
            # in case the current connection in iteration is the connection
            # that is used for the subscription (own connection) skips the
            # current loop as there's nothing to be done
            if _connection == connection: continue

            # creates the channel socket tuple containing the channel name
            # and the socket identifier for the current connection in iteration
            # and then uses it to retrieve the channel data for it, in case none
            # is retrieve must skip the current loop
            _channel_socket = (channel, _connection.socket_id)
            _channel_data = state.channel_socket_data.get(_channel_socket)
            if not _channel_data: continue

            # retrieves the user identifier for the current channel data in
            # case the user identifier is the same as the current channel's
            # identifiers ignores it (no need to subscribe to our own channel)
            # and then in case it has already been visited also ignores it
            _user_id = _channel_data["user_id"]
            if _user_id == user_id: continue
            if _user_id in visited: continue

            # subscribes for the peer channel for the user id pair and adds
            # the current user id to the list of visited ids (avoid duplicated
            # subscriptions of channels)
            self.subscribe_peer(
                app_key, connection, channel, user_id, _user_id
            )
            visited.append(_user_id)

    def unsubscribe_peer_all(self, app_key, connection, channel):
        # creates the channel socket tuple with the channel name and the
        # socket identifier for the current connection
        state = self.get_state(app_key = app_key)
        channel_socket = (channel, connection.socket_id)

        # retrieves the channel data information for the current channel
        # socket and in case there's none returns immediately
        channel_data = state.channel_socket_data.get(channel_socket)
        if not channel_data: return

        # retrieves the user identifier from the channel data of the current
        # connection in the channel
        user_id = channel_data["user_id"]

        # uses the channel information to retrieve the list of currently
        # registered connections for the channel, these are going to be
        # used in the unsubscription iteration
        info = state.channel_info.get(channel, {})
        conns = info.get("conns", [])

        # creates the list that will hold the list of user identifier
        # that have already been visited so that no more that one peer
        # unsubscription is done by type
        visited = []

        # iterates over all the connections subscribed for the current channel
        # to be able to unregister for each of the peer channels
        for _connection in conns:
            # in case the current connection in iteration is the connection
            # that is used for the subscription (own connection) skips the
            # current loop as there's nothing to be done
            if _connection == connection: continue

            # creates the channel socket tuple containing the channel name
            # and the socket identifier for the current connection in iteration
            # and then uses it to retrieve the channel data for it, in case none
            # is retrieve must skip the current loop
            _channel_socket = (channel, _connection.socket_id)
            _channel_data = state.channel_socket_data.get(_channel_socket)
            if not _channel_data: continue

            # retrieves the user identifier for the current channel data in
            # case the user identifier is the same as the current channel's
            # identifiers ignores it (no need to unsubscribe to our own channel)
            # and then in case it has already been visited also ignores it
            _user_id = _channel_data["user_id"]
            if _user_id == user_id: continue
            if _user_id in visited: continue

            # unsubscribes from the peer channel for the user id pair and adds
            # the current user id to the list of visited ids (avoid duplicated
            # subscriptions of channels)
            self.unsubscribe_peer(
                app_key, connection, channel, user_id, _user_id
            )
            visited.append(_user_id)

    def subscribe_peer(self, app_key, connection, channel, first_id, second_id):
        # in case the id of both parts is the same, must return immediately
        # as this is considered to be an invalid channel, for peer basis
        if first_id == second_id: return

        base = [first_id, second_id]; base.sort()
        base_s = "&".join(base)
        base_channel = channel[9:]
        _channel = "peer-" + base_channel + ":" + base_s
        self.subscribe(
            connection,
            app_key,
            connection.socket_id,
            _channel,
            force = True
        )

    def unsubscribe_peer(self, app_key, connection, channel, first_id, second_id):
        # in case the id of both parts is the same, must return immediately
        # as this is considered to be an invalid channel, for peer basis
        if first_id == second_id: return

        base = [first_id, second_id]; base.sort()
        base_s = "&".join(base)
        base_channel = channel[9:]
        _channel = "peer-" + base_channel + ":" + base_s
        self.unsubscribe(
            connection,
            app_key,
            connection.socket_id,
            _channel
        )

    def is_subscribed(self, app_key, socket_id, channel):
        """
        Verifies if the socket identified by the provided socket
        id is subscribed for the provided channel.

        Keep in mind that the channel should be an app id absent
        value and does not identify a channel in an unique way.

        This not a very light operation as it verifies the socket's
        associated channels structure for presence of the channel.
        Use this with care to avoid performance issues.

        :type app_key: String
        :param app_key: The app key to be used in the retrieval of
        the state for the subscription testing.
        :type socket_id: String
        :param socket_id: The identifier of the socket to be checked
        for subscription.
        :type channel: String
        :param channel: The "local" name of the channel to be verified
        for subscription in the current socket context.
        :rtype: bool
        :return: The result of the is subscribed test for the provided
        app key, socket id and channel information.
        """

        state = self.get_state(app_key = app_key)
        channels = state.socket_channels.get(socket_id, None)
        is_subscribed = channel in channels if channels else False
        return is_subscribed

    def is_eligible(self, app_key, socket_id, channel):
        # verifies if the provided channel starts with the peer prefix
        # and if that's not the case returns an invalid value immediately
        # as no eligibility test is possible for other channels
        if not channel.startswith("peer-"): return False

        # splits the channel into the base and tail parts and then extracts
        # both the base channel name and the peers list for processing
        base, tail = channel.split(":", 1)
        base_channel = "presence-" + base.split("-", 1)[1]
        peers = tail.split("&", 1)

        # retrieves the required app state from the provided app key, it's
        # going to be used for channel data related operations
        state = self.get_state(app_key = app_key)

        # constructs the channel socket tuple and uses it to retrieve the
        # the channel data value for the base channel so that the user
        # identification is retrieved for verification, note that in no
        # channel data exists the socket is considered not eligible
        channel_socket = (base_channel, socket_id)
        channel_data = state.channel_socket_data.get(channel_socket)
        if not channel_data: return False
        user_id = channel_data["user_id"]

        # returns the final boolean value for the presence testing of the
        # user id value in the peers list (as expected)
        return user_id in peers

    def trigger(
        self,
        app_id,
        event,
        data,
        channels = None,
        echo = False,
        persist = False,
        json_d = None,
        owner_id = None,
        verify = True
    ):
        if not channels: channels = ("global",)

        channels_t = type(channels)
        if not channels_t in (list, tuple): channels = (channels,)

        invalid = dict()

        for channel in channels: self.trigger_c(
            app_id,
            channel,
            event,
            echo,
            persist,
            data,
            json_d = json_d,
            owner_id = owner_id,
            verify = verify,
            invalid = invalid
        )

    def trigger_c(
        self,
        app_id,
        channel,
        event,
        echo,
        persist,
        data,
        json_d = None,
        owner_id = None,
        verify = True,
        invalid = {}
    ):
        # retrieves the data type of the provided data of the event and
        # depending on the kind of structure it may dump the result as
        # a plain based string serialized using json
        data_t = type(data)
        data = data if data_t in appier.legacy.STRINGS else json.dumps(data)

        # creates the "new" json dictionary object that represents the
        # event payload and copies some of the event metadata into it
        # so that it may be consulted latter by the client, note that
        # a copy must be created to avoid any issue related with re-usage
        json_d = dict(json_d) if json_d else dict()
        if channel: json_d["channel"] = channel
        if event: json_d["event"] = event
        if data: json_d["data"] = data

        # in case the persist flag is set the log channel operation is
        # performed so that the event is stored in the data source and
        # may be retrieved latter for reference/observation, note that
        # for these situations the mid and timestamp values are added
        # to the json information, so that they may be used for reference
        if persist:
            event_s = self.log_channel(
                app_id,
                channel,
                json_d,
                owner_id = owner_id,
                verify = verify,
                invalid = invalid
            )
            json_d["mid"] = event_s.mid
            json_d["timestamp"] = event_s.timestamp

        # runs the process of sending the event through the channel,
        # note that the process will also be run for the complete set
        # of handlers registered for the current infra-structure
        self.send_channel(
            app_id,
            channel,
            json_d,
            echo = echo,
            owner_id = owner_id,
            verify = verify,
            invalid = invalid
        )

    def get_subscriptions(self, app_id, channel):
        subscriptions = pushi.Subscription.find(
            instance = app_id,
            event = channel
        )
        return subscriptions

    def log_channel(
        self,
        app_id,
        channel,
        json_d,
        owner_id = None,
        verify = True,
        invalid = {},
        has_date = True,
        delayed = True
    ):
        # verifies that the owner (socket) identifier is present in the channel
        # (but only in case the verify flag is present)
        if owner_id and verify: self.verify_presence(app_id, owner_id, channel)

        # generates the proper event structure (includes identifiers
        # and timestamps) to the current event this structure is going
        # to be used for both handling and persistence
        event = self.gen_event(
            app_id,
            channel,
            json_d = json_d,
            owner_id = owner_id,
            has_date = has_date
        )

        def persist():
            # stores the event structure in the data source for latter usage
            # this is going to be a blocking operation and as such must be
            # used with proper care to avoid blocking of application
            event.save()

            # extracts the mid from the event so that it's does not need
            # to be extracted in every iteration
            mid = event.mid

            # retrieves the complete set of subscriptions for the
            # provided channel and under the current app id to be
            # able to create the proper associations
            subscriptions = self.get_subscriptions(app_id, channel)
            for subscription in subscriptions:
                user_id = subscription.user_id
                if user_id in invalid: continue
                assoc = pushi.Association(
                    instance = app_id,
                    mid = mid,
                    user_id = user_id
                )
                assoc.save()
                invalid[user_id] = True

        # delays the persistence of the event data and subscription so
        # that the current control flow is not blocked with the data
        # store operations that are going to be performed, in case the
        # delayed flag is not set the operation is executed immediately
        self.app.delay(persist) if delayed else persist()

        # returns the final generated event structure that may be used
        # to retrieve some persistent related information (eg: mid)
        return event

    def send_channel(
        self,
        app_id,
        channel,
        json_d,
        echo = False,
        owner_id = None,
        verify = True,
        invalid = {}
    ):
        # tries to retrieve the value of the flag that controls if the
        # "custom" handlers should be used for the channel handling
        use_handlers = appier.conf("PUSHI_HANDLERS", True, cast = bool)

        # retrieves the state of the current app to be used in the sending and
        # verifies that the owner (socket) identifier is present in the channel
        # (but only in case the verify flag is present)
        state = self.get_state(app_id = app_id)
        if owner_id and verify: self.verify_presence(app_id, owner_id, channel)

        # retrieves the complete set of sockets associated with the channel
        # and sends the json data through the socket, avoiding sending the
        # data through the same socket that originated the event, unless the
        # echo flag is set (meaning re-sending to channel)
        sockets = state.channel_sockets.get(channel, [])
        for socket_id in sockets:
            if socket_id in invalid: continue
            if socket_id == owner_id and not echo: continue
            self.send_socket(socket_id, json_d)
            invalid[socket_id] = True

        # in case the handlers should not be used for custom handling the
        # control flow should be returned immediately as expected
        if not use_handlers: return

        # iterates over the complete set of handler currently defined
        # to send the message also through these channels, in case there's
        # a failure the event is logged to avoid unwanted exceptions
        for handler in self.handlers:
            try:
                handler.send(app_id, channel, json_d, invalid = invalid)
            except BaseException as exception:
                self.app.logger.info(
                    "Problem using handler '%s' for sending - %s" %
                    (handler.name, appier.legacy.UNICODE(exception))
                )

    def send_socket(self, socket_id, json_d):
        self.server.send_socket(socket_id, json_d)

    def get_state(self, app_id = None, app_key = None):
        # sets the initial value of the state value as invalid so
        # that by default the returned value is invalid
        state = None

        # in case no app id and no app key are provided there's no
        # way to retrieve the app state (no identifier) and as such
        # must raise an exception indicating the problem
        if not app_id and not app_key:
            raise RuntimeError("No app identifier was provided")

        # retrieves the state object taking into account first the
        # app id and then the app key (as an alternative) after this
        # call the state object should be populated
        if app_id: state = self.app_id_state.get(app_id, None)
        elif app_key: state = self.app_key_state.get(app_key, None)

        # in case the state object is found (already created) returns
        # the value immediately (to the caller method)
        if state: return state

        # retrieves the app object for the provided parameters and in case
        # the app is not found raises an exception indicating so
        app = self.get_app(app_id = app_id, app_key = app_key)
        if not app: raise RuntimeError("No app found for the provided parameters")

        # unpacks both the app id and key values from the app object
        # to be used in the construction of the app state object
        app_id = app.ident
        app_key = app.key

        # creates the (app) state object with the provided app id and key
        # and the updates the associated dictionaries to access the app state
        # from both the app id and key values
        state = AppState(app_id, app_key)
        self.app_id_state[app_id] = state
        self.app_key_state[app_key] = state

        # returns the creates state object to the caller method, as requested
        # (this state object has just been created)
        return state

    def get_channel(self, app_key, channel, skip = 0, count = 10, limit = True):
        members = self.get_members(app_key, channel)
        alias = self.get_alias(app_key, channel)
        events = self.get_events(
            app_key,
            channel,
            skip = skip,
            count = count,
            limit = limit
        )
        return dict(
            name = channel,
            members = members,
            alias = alias,
            events = events
        )

    def get_members(self, app_key, channel):
        state = self.get_state(app_key = app_key)
        info = state.channel_info.get(channel, {})
        members = info.get("members", {})
        return members

    def get_alias(self, app_key, channel):
        state = self.get_state(app_key = app_key)
        return state.alias.get(channel, [])

    def get_channels(self, app_key, alias):
        state = self.get_state(app_key = app_key)
        return state.alias_i.get(alias, [])

    def get_events(self, app_key, channel, skip = 0, count = 10, limit = True, map = True):
        is_personal = channel.startswith("personal-")
        if not is_personal and limit: return []

        if is_personal: return self.get_events_personal(
            app_key,
            channel,
            skip = skip,
            count = count,
            map = map
        )
        else: return self.get_events_global(
            app_key,
            channel,
            skip = skip,
            count = count,
            map = map
        )

    def get_events_global(self, app_key, channel, skip = 0, count = 10, map = True):
        app_id = self.app_key_to_app_id(app_key)
        events = pushi.PushiEvent.find(
            instance = app_id,
            channel = channel,
            skip = skip,
            limit = count,
            sort = [("_id", -1)],
            map = map
        )
        for event in events: del event["_id"]
        return events

    def get_events_personal(self, app_key, channel, skip = 0, count = 10, map = True):
        user_id = channel[9:]
        app_id = self.app_key_to_app_id(app_key)

        assocs = pushi.Association.find(
            instance = app_id,
            user_id = user_id,
            skip = skip,
            limit = count,
            sort = [("_id", -1)]
        )
        mids = [assoc.mid for assoc in assocs]

        events = pushi.PushiEvent.find(
            instance = app_id,
            mid = {"$in" : mids},
            sort = [("_id", -1)],
            map = map
        )
        for event in events: del event["_id"]

        return events

    def get_app(self, app_id = None, app_key = None, raise_e = True):
        if app_id: app = pushi.App.get(ident = app_id, raise_e = raise_e)
        if app_key: app = pushi.App.get(key = app_key, raise_e = raise_e)
        return app

    def has_app(self, app_id = None, app_key = None):
        # verifies if state is currently defined for the
        # provided app values and if that's the case returns
        # immediately with a valid value
        if self.has_state(app_id = app_id, app_key = app_key): return True

        # tries to retrieve an app for the provided values
        # and in case there's one an app is considered to
        # exist (returns a valid value)
        app = self.get_app(app_id = app_id, app_key = app_key, raise_e = False)
        if app: return True

        # by default an invalid value is returned as none of the
        # verifications is considered successful
        return False

    def has_state(self, app_id = None, app_key = None):
        # verifies if either the app id or the app key are
        # present in the respective state maps and if that's
        # the case returns a valid value (presence validated)
        if app_id in self.app_id_state: return True
        if app_key in self.app_key_state: return True
        return False

    def invalidate(self, app_id = None, app_key = None):
        """
        Invalidates the state of the app for the provided identifier
        and key values. Note that the invalidated partials are only
        affected when the provided identification and key parts are
        properly provided.

        This method should be used with extreme care as unwanted results
        may emerge from wreckless usage of this method.

        :type app_id: String
        :param app_id: The identifier of the application that is going
        to be invalidated for the current state.
        :type app_key: String
        :param app_key: The key of the application that is going
        to be invalidated for the current state.
        """

        if app_id and app_id in self.app_id_state: del self.app_id_state[app_id]
        if app_key and app_key in self.app_id_state: del self.app_id_state[app_key]

    def verify(self, app_key, socket_id, channel, auth):
        """
        Verifies the provided auth (token) using the app
        secret associated with the app with the provided
        app key.

        This operation is required for the private channels
        so that only the authenticated user are allowed.

        The verification operation will raise an exception in
        the signature generated is not valid (verification has
        failed for security reasons).

        :type app_key: String
        :param app_key: The app key for the app that is going
        to be used as the base for the verification.
        :type socket_id: String
        :param socket_id: The identifier of the socket that is
        going to be used in the process of verification.
        :type channel: String
        :param channel: The name of the channel that is going
        to be used in the verification process.
        :type auth: String
        :param auth: The string that is going to be used for auth
        this should be an hmac based token string.
        """

        app = self.get_app(app_key = app_key)
        app_secret = app.secret
        app_secret = appier.legacy.bytes(str(app_secret))

        string = "%s:%s" % (socket_id, channel)
        string = appier.legacy.bytes(string)
        structure = hmac.new(app_secret, string, hashlib.sha256)
        digest = structure.hexdigest()
        auth_v = "%s:%s" % (app_key, digest)

        if not auth == auth_v: raise RuntimeError("Invalid signature")

    def verify_presence(self, app_id, socket_id, channel):
        state = self.get_state(app_id = app_id)
        channels = state.socket_channels.get(socket_id, [])
        if not channel in channels:
            raise RuntimeError("Socket '%s' is not allowed for '%s'" % (socket_id, channel))

    def app_id_to_app_key(self, app_id):
        state = self.get_state(app_id = app_id)
        return state.app_key

    def app_key_to_app_id(self, app_key):
        state = self.get_state(app_key = app_key)
        return state.app_id

    def gen_event(self, app_id, channel, json_d, owner_id = None, has_date = True):
        """
        Generates the complete event structure from the provided
        details on the current context.

        Anyone using this method should not expect the same
        results from two different calls as this method includes
        some random string generation.

        :type app_id: String
        :param app_id: The identifier of the app that is currently
        being used for the the event sending.
        :type channel: String
        :param channel: The name of the channel that is going to be
        used for sending the event.
        :type json_d: Dictionary
        :param json_d: The map containing all the (payload) information
        that is the proper event.
        :type owner_id: String
        :param owner_id: The identifier used by the entity that "owns"
        the event to be sent.
        :type has_date: bool
        :param has_date: If the generates event structure should include
        the data in its structure, this account for more processing.
        :rtype: PushiEvent
        :return: The generated event structure that was created according
        to the provided details for generation.
        """

        # runs a series of initial pre condition verification to ensure that
        # the data is ready to be persisted if required
        appier.verify(not "mid" in json_d)
        appier.verify(not "timestamp" in json_d)

        # generates a globally unique identifier that is going to be the
        # sole unique value for the event, this may be used latter for
        # unique unique identification
        mid = str(uuid.uuid4())

        # generates a timestamp that is going to identify the timing of the
        # event this value should not be trusted as this does not represent
        # the time of sending of the event but instead the generation of
        # the global event structure
        timestamp = time.time()

        # creates the proper dictionary of the event that includes all of the
        # main values of it, together with the ones that have been generated
        event = pushi.PushiEvent(
            mid = mid,
            instance = app_id,
            channel = channel,
            owner_id = owner_id,
            timestamp = timestamp,
            data = dict(json_d)
        )

        # in case the date inclusion flag is set a new date string must be
        # generates and attached to the current event structure (extra values)
        if has_date:
            date = datetime.datetime.utcfromtimestamp(timestamp)
            date_s = date.strftime("%B %d, %Y %H:%M:%S UTC")
            event.date = date_s

        # returns the "final" event structure to the caller method so that it
        # can be used as the complete event structure
        return event

if __name__ == "__main__":
    state = State()
    app = pushi.PushiApp(state)
    server = pushi.PushiServer(state)
    state.load(app, server)
else:
    __path__ = []
