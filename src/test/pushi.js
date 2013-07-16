var Pushi = function(appKey, options) {
    var URL = "ws://localhost:9090/";
    var self = this;

    this.appKey = appKey;
    this.options = options || {};
    this.socket = new WebSocket(URL);
    this.socketId = null;
    this.state = "disconnected";

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

jQuery(document).ready(function() {
            var pushi = new Pushi("asdasd");
        });
