// Hive Pushi Framework
// Copyright (C) 2008-2012 Hive Solutions Lda.
//
// This file is part of Hive Pushi Framework.
//
// Hive Pushi Framework is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// Hive Pushi Framework is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with Hive Pushi Framework. If not, see <http://www.gnu.org/licenses/>.

// __author__    = João Magalhães <joamag@hive.pt>
// __version__   = 1.0.0
// __revision__  = $LastChangedRevision$
// __date__      = $LastChangedDate$
// __copyright__ = Copyright (c) 2010-2012 Hive Solutions Lda.
// __license__   = GNU General Public License (GPL), Version 3

var PUSHI_CONNECTIONS = {}

var Channel = function(pushi, name) {
    this.pushi = pushi;
    this.name = name;
};

Channel.prototype.trigger = function(event, data) {
    this.pushi.sendChannel(event, data, this.name);
};

var Pushi = function(appKey, options) {
    var TIMEOUT = 5000;
    var BASE_URL = "wss://puxiapp.com/";

    var timeout = options.timeout || TIMEOUT;
    var baseURL = options.baseUrl || BASE_URL;

    var previous = PUSHI_CONNECTIONS[appKey];
    if (previous) {
        return this.clone(previous);
    }

    this.socket = null;
    this.timeoutT = timeout;
    this.url = baseURL + appKey;

    this.appKey = appKey;
    this.options = options || {};
    this.socketId = null;
    this.state = "disconnected";
    this.channels = {};
    this.events = {};
    this.auths = {};
    this._base = null;
    this._cloned = false;

    this.authEndpoint = this.options.authEndpoint;

    PUSHI_CONNECTIONS[appKey] = this;

    this.init();
};

Pushi.prototype.clone = function(base) {
    this.timeout = base.timeout;
    this.url = base.url
    this.appKey = base.appKey;
    this.options = base.options;
    this.socket = base.socket;
    this.socketId = base.socketId;
    this.state = base.state;
    this.channels = [];
    this.events = [];
    this.auths = base.auths;
    this.authEndpoint = base.authEndpoint;
    this._base = base;
    this._cloned = true;

    this.socket.subscriptions.push(this);

    // in case the current state of the connection is
    // connected must simulate the connection by calling
    // the appropriate handler with the correct data
    if (this.state == "connected") {
        var data = {
            socket_id : this.socketId
        };
        this.onoconnect(data);
    }
};

Pushi.prototype.init = function() {
    var self = this;
    var subscriptions = this.socket ? this.socket.subscriptions : [this];

    // creates the new websocket reference with the currently defined
    // url and then updates the reference to the underlying subscriptions
    var socket = new WebSocket(this.url);
    socket.subscriptions = subscriptions;

    // creates the function that will initialize the instance's socket to
    // the one that has now been created and then calls it to all the
    // subscriptor of the current socket
    var _init = function() {
        this.socket = socket;
    };
    this.callobj(_init, subscriptions);

    this.socket.onopen = function() {
    };

    this.socket.onmessage = function(event) {
        var message = event.data;
        var json = JSON.parse(message);

        var isConnected = self.state == "disconnected"
                && json.event == "pusher:connection_established";

        if (isConnected) {
            var data = JSON.parse(json.data);
            self.callobj(Pushi.prototype.onoconnect, this.subscriptions, data);
        } else if (self.state == "connected") {
            var data = json;
            self.callobj(Pushi.prototype.onmessage, this.subscriptions, data);
        }
    };

    this.socket.onclose = function() {
        self.callobj(Pushi.prototype.onodisconnect, this.subscriptions);
    };
};

Pushi.prototype.callobj = function(callable, objects) {
    var args = [];

    for (var index = 2; index < arguments.length; index++) {
        args.push(arguments[index])
    }

    for (var index = 0; index < objects.length; index++) {
        var _object = objects[index];
        callable.apply(_object, args);
    }
};

Pushi.prototype.retry = function() {
    // sets the current object context in the self variable
    // to be used by the clojures that are going to be created
    var self = this;

    // in case this is a cloned object the retry operation
    // is not possible because this object does not owns
    // the underyling websocket object
    if (this._cloned) {
        return;
    }

    // sets the timeout for the new initialization of the
    // object this value should not be to low that congests
    // the server side nor to large that takes to long for
    // the reconnection to take effect (bad user experience)
    setTimeout(function() {
                self.init();
            }, this.timeout);
};

Pushi.prototype.trigger = function(event) {
    var methods = this.events[event] || [];
    for (var index = 0; index < methods.length; index++) {
        var method = methods[index];
        method.apply(this, arguments);
    }
};

Pushi.prototype.bind = function(event, method) {
    var methods = this.events[event] || [];
    methods.push(method);
    this.events[event] = methods;
};

Pushi.prototype.unbind = function(event, method) {
    var methods = this.events[event] || [];
    var index = methods.indexOf(method);
    index && methods.splice(index, 1);
};

Pushi.prototype.onoconnect = function(data) {
    this.socketId = data.socket_id;
    this.state = "connected";
    this.trigger("connect");
};

Pushi.prototype.onodisconnect = function(data) {
    this.socketId = null;
    this.channels = {};
    this.state = "disconnected";
    this.trigger("disconnect");
    this.retry();
};

Pushi.prototype.onsubscribe = function(channel, data) {
    this.trigger("subscribe", channel, data);
};

Pushi.prototype.onmemberadded = function(channel, member) {
    this.trigger("member_added", channel, member);
};

Pushi.prototype.onmemberremoved = function(channel, member) {
    this.trigger("member_removed", channel, member);
};

Pushi.prototype.onmessage = function(json) {
    var channel = json.channel;
    var _channel = this.channels[channel];
    var isPeer = channel.startsWith("peer-");
    if (channel && !_channel && !isPeer) {
        return;
    }

    switch (json.event) {
        case "pusher_internal:subscription_succeeded" :
            var data = JSON.parse(json.data);
            this.onsubscribe(json.channel, data);
            break;

        case "pusher:member_added" :
            var member = JSON.parse(json.member);
            this.onmemberadded(json.channel, member);
            break;

        case "pusher:member_removed" :
            var member = JSON.parse(json.member);
            this.onmemberremoved(json.channel, member);
            break;
    }

    this.trigger(json.event, json.data, json.channel);
};

Pushi.prototype.send = function(json) {
    var data = JSON.stringify(json);
    this.socket.send(data);
};

Pushi.prototype.sendEvent = function(event, data) {
    var json = {
        event : event,
        data : data
    };
    this.send(json);
};

Pushi.prototype.sendChannel = function(event, data, channel) {
    var json = {
        event : event,
        data : data,
        channel : channel
    };
    this.send(json);
};

Pushi.prototype.subscribe = function(channel) {
    var self = this;

    var _channel = this.channels[channel];
    if (_channel) {
        return _channel;
    }

    // in case this is a cloned proxy object we must also
    // check if the base object is already subscribed for
    // the channel for such cases the callback should be
    // called immediately as there's no remote call to be
    // performed for such situations
    if (this._cloned) {
        var _channel = this._base.channels[channel];
        if (_channel) {
            setTimeout(function() {
                        self.onsubscribe(channel);
                    });
            this.channels[channel] = _channel;
            return _channel;
        }
    }

    // verifies if the current channel to be subscribed
    // is of type private and in case it is uses the proper
    // private way of subscription otherwise uses the public
    // way for subscription (no authentication process)
    var isPrivate = channel.startsWith("private-")
            || channel.startsWith("presence-");
    if (isPrivate) {
        this.subscribePrivate(channel);
    } else {
        this.subscribePublic(channel);
    }

    var name = channel;
    var channel = new Channel(this, name);
    this.channels[name] = channel;

    return channel;
};

Pushi.prototype.subscribePublic = function(channel) {
    this.sendEvent("pusher:subscribe", {
                channel : channel
            });
};

Pushi.prototype.subscribePrivate = function(channel) {
    // in case no authentication endpoint exists returns imediately
    // because there's not enough information to proceed with the
    // authentication process for the private channel
    if (!this.authEndpoint) {
        throw "No auth endpoint defined";
    }

    // sets the current context in the self variable to be
    // used by the clojures in the current function
    var self = this;

    // contructs the get query part of the url with both the socket
    // id of the current connection and the channel value for it
    // then constructs the complete url value for the connection
    var query = "?socket_id=" + this.socketId + "&channel=" + channel;
    var url = this.authEndpoint + query;

    // creates the remote async request that it's going
    // to be used to retrieve the authentication information
    // this is going to use the provided auth endpoint together
    // with some of the current context
    var request = new XMLHttpRequest();
    request.open("get", url, true);
    request.onreadystatechange = function() {
        // in case the current state is not ready returns
        // immediately as it's not a (to) success change
        if (request.readyState != 4) {
            return;
        }

        // retrieves the reponse data and parses it as a json
        // message and returns immediately in case no auth
        // information is provided as part of the response
        var result = JSON.parse(request.responseText);
        if (!result.auth) {
            return;
        }

        // sends a pusher subscribe event containing all of the
        // channel information together with the auth token and
        // the channel data to be used (in case it exists)
        self.sendEvent("pusher:subscribe", {
                    channel : channel,
                    auth : result.auth,
                    channel_data : result.channel_data
                });
    };
    request.send();
};

if (typeof String.prototype.startsWith != "function") {
    String.prototype.startsWith = function(string) {
        return this.slice(0, string.length) == string;
    };
}
