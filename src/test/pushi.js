var Pushi = function(appKey, options) {
    var URL = "ws://localhost:9090/";
    var self = this;

    this.appKey = appKey;
    this.options = options || {};
    this.socket = new WebSocket(URL);
    this.socketId = null;
    this.state = "disconnected";
    this.events = {};

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
    this.subscribe("global");
};

Pushi.prototype.onodisconnect = function() {
};

Pushi.prototype.onsubscribe = function(channel) {
};

Pushi.prototype.onmessage = function(json) {
    switch (json.event) {
        case "pusher_internal:subscription_succeeded" :
            this.onsubscribe(json.channel);
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

Pushi.prototype.subscribe = function(channel) {
    this.sendEvent("pusher:subscribe", {
                channel : channel
            });
};
