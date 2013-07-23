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

var Channel = function(pushi, name) {
    this.pushi = pushi;
    this.name = name;
};

Channel.prototype.trigger = function(event, data) {
    this.pushi.sendChannel(event, data, this.name);
};

var Pushi = function(appKey, options) {
    var BASE_URL = "ws://localhost:9090/";
    var self = this;

    this.url = BASE_URL + appKey

    this.appKey = appKey;
    this.options = options || {};
    this.socket = new WebSocket(this.url);
    this.socketId = null;
    this.state = "disconnected";
    this.events = {};
    this.auths = {}

    this.authEndpoint = this.options.authEndpoint;

    this.socket.onopen = function() {
    };

    this.socket.onmessage = function(event) {
        var message = event.data;
        var json = JSON.parse(message);

        if (self.state == "disconnected"
                && json.event == "pusher:connection_established") {
            var data = JSON.parse(json.data);
            self.socketId = data.socket_id;
            self.state = "connected";
            self.onoconnect();
        } else if (self.state == "connected") {
            self.onmessage(json);
        }
    };

    this.socket.onclose = function() {
        self.socketId = null;
        self.state == "disconnected";
        self.onodisconnect();
    };
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

Pushi.prototype.onoconnect = function() {
    this.trigger("connect");
};

Pushi.prototype.onodisconnect = function() {
    this.trigger("disconnect");
};

Pushi.prototype.onsubscribe = function(channel) {
    this.trigger("subscribe", channel);
};

Pushi.prototype.onmemberadded = function(channel, member) {
    this.trigger("member_added", channel, member);
};

Pushi.prototype.onmemberremoved = function(channel, member) {
    this.trigger("member_removed", channel, member);
};

Pushi.prototype.onmessage = function(json) {
    switch (json.event) {
        case "pusher_internal:subscription_succeeded" :
            this.onsubscribe(json.channel);
            break;

        case "pusher:member_added" :
            this.onmemberadded(json.channel, json.member);
            break;

        case "pusher:member_removed" :
            this.onmemberremoved(json.channel, json.member);
            break;
    }

    this.trigger(json.event, json.data);
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
    var isPrivate = channel.startsWith("private-")
            || channel.startsWith("presence-");
    if (isPrivate) {
        return this.subscribePrivate(channel);
    }

    this.sendEvent("pusher:subscribe", {
                channel : channel
            });

    var channel = new Channel(this, channel);
    return channel;
};

Pushi.prototype.subscribePrivate = function(channel) {
    if (!this.authEndpoint) {
        throw "No auth endpoint defined";
    }

    var self = this;
    var query = "?socket_id=" + this.socketId + "&channel=" + channel;
    var url = this.authEndpoint + query;

    var request = new XMLHttpRequest();
    request.open("get", url, true);
    request.onreadystatechange = function() {
        if (request.readyState != 4) {
            return;
        }

        var result = JSON.parse(request.responseText);
        if (!result.auth) {
            return;
        }

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
