#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (C) 2008-2012 Hive Solutions Lda.
#
# This file is part of Hive Pushi System.
#
# Hive Pushi System is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Hive Pushi System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Hive Pushi System. If not, see <http://www.gnu.org/licenses/>.

__author__ = "João Magalhães joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2012 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "GNU General Public License (GPL), Version 3"
""" The license for the module """

import os
import sys
import time
import json
import hmac
import uuid
import copy
import types
import hashlib
import datetime
import threading

base_dir = (os.path.normpath(os.path.dirname(__file__) or ".") + "/../..")
if not base_dir in sys.path: sys.path.insert(0, base_dir)

import pushi
import appier

import apn

class AppState(object):
    """
    The state object that defined the various state variables
    for an app registered in the system. There should be one
    of this objects per each application loaded.
    """

    def __init__(self, app_id, app_key):
        self.app_id = app_id
        self.app_key = app_key
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

        # "moves" the (in memory) logging handler of the app to the
        # server so that they share a common logging infrastructure
        handler = self.app.handler
        self.server.handler = handler

        # registers for the various base events in the server so that
        # it's able to properly update the current state of the application
        # to the new state (according to the operation)
        self.server.bind("connect", self.connect)
        self.server.bind("disconnect", self.disconnect)
        self.server.bind("subscribe", self.subscribe)

        # retrieves the various environment variable values that are going
        # to be used in the starting of both the app server and the proper
        # pushi server (most of the values have default values)
        APP_SERVER = os.environ.get("APP_SERVER", "waitress")
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
            cer_file = APP_SSL_CER,
        )
        server_kwargs = dict(
            host = SERVER_HOST,
            port = SERVER_PORT,
            ssl = SERVER_SSL,
            key_file = SERVER_SSL_KEY,
            cer_file = SERVER_SSL_CER,
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
        self.apn_handler = apn.ApnHandler(self)
        self.apn_handler.load()

        self.handlers.append(self.apn_handler)

    def load_alias(self):
        """
        Loads the complete set of alias (channels that represent) the
        same for the current context, this may be used for a variety
        of reasons including the personal channels.
        """

        # creates the map that associates the alias with the
        # channels that it represents key to values association
        self.alias = {}

        # retrieves the reference to the database and uses it to
        # find the complete set of subscriptions and then uses them
        # to create the complete personal to proper channel relation
        db = self.get_db("pushi")
        subs = db.subs.find()
        for sub in subs:
            app_id = sub["app_id"]
            user_id = sub["user_id"]
            event = sub["event"]
            app_key = self.app_id_to_app_key(app_id)
            self.add_alias(app_key, "personal-" + user_id, event)

    def connect(self, connection, app_key, socket_id):
        pass

    def disconnect(self, connection, app_key, socket_id):
        # in case no app key or socket id is defined must return
        # immediately because it's not possible to perform the
        # disconnect operation in such conditions, possible a non
        # established connection is attempting to disconnect
        if not app_key: return
        if not socket_id: return

        # retrieves the current state of the app using the app key and
        # then uses it to retrieve the complete set of channels that the
        # socket is subscribed and then unsubscribe it from them then
        # removes the reference of the socket in the socket channels map
        state = self.get_state(app_key = app_key)
        channels = state.socket_channels.get(socket_id, [])
        channels = copy.copy(channels)
        for channel in channels: self.unsubscribe(connection, app_key, socket_id, channel)
        if socket_id in state.socket_channels: del state.socket_channels[socket_id]

    def subscribe(self, connection, app_key, socket_id, channel, auth = None, channel_data = None, force = False):
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
        # connection from it (avoid duplicated registration)
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
        channels.append(channel)
        state.socket_channels[socket_id] = channels

        # retrieves the complete set of sockets for the channels (inverted)
        # association and adds the current socket id to the list then
        # re-updates the inverted map with the sockets list
        sockets = state.channel_sockets.get(channel, [])
        sockets.append(socket_id)
        state.channel_sockets[channel] = sockets

        # in case there's no channel data to be used to change
        # metadata and in additional processing must return
        # immediately as there's nothing else remaining to be
        # done in the subscription process
        if not channel_data: return

        user_id = channel_data["user_id"]
        is_peer = channel_data.get("peer", False)

        state.channel_socket_data[channel_socket] = channel_data

        info = state.channel_info.get(channel, {})
        users = info.get("users", {})
        members = info.get("members", {})
        conns = info.get("conns", [])
        user_count = info.get("user_count", 0)

        conns.append(connection)

        user_conns = users.get(user_id, [])
        user_conns.append(connection)
        users[user_id] = user_conns
        members[user_id] = channel_data

        is_new = len(user_conns) == 1
        if is_new: user_count += 1

        info["users"] = users
        info["members"] = members
        info["conns"] = conns
        info["user_count"] = user_count
        state.channel_info[channel] = info

        # subscribes all of the peer channels associated with the current
        # presence channel that is being subscribed, this may represent some
        # overhead but provides peer to peer communication
        is_peer and self.subscribe_peer_all(app_key, connection, channel)

        if not is_new: return

        json_d = dict(
            event = "pusher:member_added",
            member = json.dumps(channel_data),
            channel =  channel
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

        is_empty = len(conns) == 0
        if is_empty: del state.channel_info[channel]

        json_d = dict(
            event = "pusher:member_removed",
            member = json.dumps(channel_data),
            channel =  channel
        )

        for _connection in conns:
            if _connection == connection: continue
            _connection.send_pushi(json_d)

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

            _user_id = _channel_data["user_id"]
            self.unsubscribe_peer(
                app_key, _connection, channel, user_id, _user_id
            )

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
        if first_id == second_id: return

        base = [first_id, second_id]; base.sort()
        base_s = "_".join(base)
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
        if first_id == second_id: return

        base = [first_id, second_id]; base.sort()
        base_s = "_".join(base)
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

        @type app_key: String
        @param app_key: The app key to be used in the retrieval of
        the state for the subscription testing.
        @type socket_id: String
        @param socket_id: The identifier of the socket to be checked
        for subscription.
        @type channel: String
        @param channel: The "local" name of the channel to be verified
        for subscription in the current socket context.
        @rtype: bool
        @return: The result of the is subscribed test for the provided
        app key, socket id and channel information.
        """

        state = self.get_state(app_key = app_key)
        channels = state.socket_channels.get(socket_id, None)
        is_subscribed = channel in channels if channels else False
        return is_subscribed

    def add_alias(self, app_key, channel, alias):
        alias_m = self.alias.get(app_key, {})
        alias_l = alias_m.get(channel, [])
        if alias in alias_l: return

        alias_l.append(alias)
        alias_m[channel] = alias_l
        self.alias[app_key] = alias_m

    def remove_alias(self, app_key, channel, alias):
        alias_m = self.alias.get(app_key, {})
        alias_l = alias_m.get(channel, [])
        if not alias in alias_l: return

        alias_l.remove(alias)

    def get_alias(self, app_key, channel):
        alias_m = self.alias.get(app_key, {})
        return alias_m.get(channel, [])

    def get_events(self, app_key, channel, count = 10):
        is_personal = channel.startswith("personal-")
        if not is_personal: return []

        user_id = channel[9:]
        app_id = self.app_key_to_app_id(app_key)

        db = self.get_db("pushi")
        assoc = dict(
            app_id = app_id,
            user_id = user_id
        )
        cursor = db.assoc.find(
            assoc,
            limit = count,
            sort = [("_id", -1)]
        )
        mids = [assoc["mid"] for assoc in cursor]

        event = dict(mid = {"$in" : mids})
        cursor = db.event.find(event, sort = [("_id", -1)])
        events = [event for event in cursor]
        for event in events: del event["_id"]

        return events

    def trigger(self, app_id, event, data, channels = None, owner_id = None):
        if not channels: channels = ("global",)

        for channel in channels: self.trigger_c(
            app_id,
            channel,
            event,
            data,
            owner_id = owner_id
        )

    def trigger_c(self, app_id, channel, event, data, owner_id = None, verify = True):
        data_t = type(data)
        data = data if data_t in types.StringTypes else json.dumps(data)

        json_d = dict(
            channel = channel,
            event = event,
            data = data
        )
        self.log_channel(
            app_id,
            channel,
            json_d,
            owner_id = owner_id
        )
        self.send_channel(
            app_id,
            channel,
            json_d,
            owner_id = owner_id,
            verify = verify
        )

    def get_subscriptions(self, app_id, channel):
        db = self.get_db("pushi")
        subscription = dict(
            app_id = app_id,
            event = channel
        )
        cursor = db.subs.find(subscription)
        subscriptions = [subscription for subscription in cursor]
        return subscriptions

    def log_channel(self, app_id, channel, json_d, owner_id = None, has_date = True):
        # retrieves the reference to the pushi database that is going
        # to be used for the operation in the logging
        db = self.get_db("pushi")

        # generates the proper event structure (includes identifiers
        # and timestamps) to the current event and then adds it to
        # the list of events registered in the data source
        event = self.gen_event(
            app_id,
            channel,
            json_d = json_d,
            owner_id = owner_id,
            has_date = has_date
        )
        db.event.insert(event)

        # retrieves the complete set of subscription for the
        # provided channel and under the current app id to be
        # able to create the proper associations
        subscriptions = self.get_subscriptions(app_id, channel)
        for subscription in subscriptions:
            assoc = dict(
                app_id = app_id,
                mid = event["mid"],
                user_id = subscription["user_id"]
            )
            db.assoc.insert(assoc)

    def send_channel(self, app_id, channel, json_d, owner_id = None, verify = True):
        state = self.get_state(app_id = app_id)
        if owner_id and verify: self.verify_presence(app_id, owner_id, channel)
        sockets = state.channel_sockets.get(channel, [])
        for socket_id in sockets:
            if socket_id == owner_id: continue
            self.send_socket(socket_id, json_d)

        # iterates over the complete set of handler currently defined
        # to send the message also through these channels, in case there's
        # a failure the event is logged to avoid unwanted exceptions
        for handler in self.handlers:
            try:
                handler.send(app_id, channel, json_d)
            except BaseException, exception:
                self.app.logger.info(
                    "Problem using handler '%s' for sending - %s" %\
                    (handler.name, unicode(exception))
                )

    def send_socket(self, socket_id, json_d):
        self.server.send_socket(socket_id, json_d)

    def get_state(self, app_id = None, app_key = None):
        state = None

        if not app_id and not app_key:
            raise RuntimeError("No app identifier was provided")

        if app_id: state = self.app_id_state.get(app_id, None)
        if app_key: state = self.app_key_state.get(app_key, None)

        if state: return state

        app = self.get_app(app_id = app_id, app_key = app_key)
        if not app: raise RuntimeError("No app found for the provided parameters")

        app_id = app["app_id"]
        app_key = app["key"]

        state = AppState(app_id, app_key)
        self.app_id_state[app_id] = state
        self.app_key_state[app_key] = state

        return state

    def get_channel(self, app_key, channel):
        members = self.get_members(app_key, channel)
        alias = self.get_alias(app_key, channel)
        events = self.get_events(app_key, channel)
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

    def get_app(self, app_id = None, app_key = None):
        db = self.get_db("pushi")
        if app_id: app = db.app.find_one(dict(app_id = app_id))
        if app_key: app = db.app.find_one(dict(key = app_key))
        return app

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

        @type app_key: String
        @param app_key: The app key for the app that is going
        to be used as the base for the verification.
        @type socket_id: String
        @param socket_id: The identifier of the socket that is
        going to be used in the process of verification.
        @type channel: String
        @param channel: The name of the channel that is going
        to be used in the verification process.
        @type auth: String
        @param auth: The string that is going to be used for auth
        this should be an hmac based token string.
        """

        app = self.get_app(app_key = app_key)
        app_secret = app["secret"]

        string = "%s:%s" % (socket_id, channel)
        structure = hmac.new(str(app_secret), str(string), hashlib.sha256)
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

        @type app_id: String
        @param app_id: The identifier of the app that is currently
        being used for the the event sending.
        @type channel: String
        @param channel: The name of the channel that is going to be
        used for sending the event.
        @type json_d: Dictionary
        @param json_d: The map containing all the (payload) information
        that is the proper event.
        @type owner_id: String
        @param owner_id: The identifier used by the entity that "owns"
        the event to be sent.
        @type has_date: bool
        @param has_date: If the generates event structure should include
        the data in its structure, this account for more processing.
        @rtype: Dictionary
        @return: The generated event structure that was created according
        to the provided details for generation.
        """

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
        event = dict(
            mid = mid,
            app_id = app_id,
            channel = channel,
            owner_id = owner_id,
            timestamp = timestamp,
            data = json_d
        )

        # in case the date inclusion flag is set a new date string must be
        # generates and attached to the current event structure (extra values)
        if has_date:
            date = datetime.datetime.utcfromtimestamp(timestamp)
            date_s = date.strftime("%B %d, %Y %H:%M:%S UTC")
            event["date"] = date_s

        # returns the "final" event structure to the caller method so that it
        # can be used as the complete event structure
        return event

if __name__ == "__main__":
    state = State()
    app = pushi.PushiApp(state)
    server = pushi.PushiServer(state)
    state.load(app, server)
