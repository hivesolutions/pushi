# Pushi Websockets

Simple yet powerfull infra-structure for handling of websocket connection.

## Objectives

The server itself should be based on a common infra-structure like the one
present in frameworks like node.js that should abstract the socket connection
layer (select layer) on an event driven basis. The infra-structure itself should
be nonblocking and asyncronous for performance and saclability.

The API layer should be provided by a simple WSGI application implemented using
the [appier framework](https://github.com/hivesolutions/appier) to keep things
simple and fast.

For persistence the pushi infra-structure uses the MongoDB database infra-structure
to avoid any unwanted complexities and provide fast performance.

## Inspiration

Pushi was heavily inspired by the [Pusher](http://pusher.com) service, and aims
at providing a free alternative to it (for cost reducing).

## Channels

The channel is the base object for communication and there are four types of channels
so that each one has its own objectives.

### Public Channels

Channels that may be subscribed by any connection without any sort of validation.

### Private Channels

Authenticated channels that for which the access is constrained to only server side
validated connections.

### Presence Channels

Channels that provide extra information on the situation on the channel, for instance
allow the identification of a set of connection using a single `user_id` tag. Using
this approach it's possible to know when a new user connects to the channel and when
one disconnect (no more connection with the same `user_id` are present). These channels
are considered private and so are subject to validation from the server side.

### Peer Channels

Targeted at chat environment allows for the creation of automatic channels for the
various elements (users) that are subscribed to a peer channel. The activation of the
automatic peer channel configuration is archieved using the `peer` flag in the `channel_data`.
This channel type **should not be created directly**.

## Running

To be able to run the pushi infra-structure under a normal non ecrypted connection
and bind to the complete set of network interfaces in the host the following command:

    APP_HOST=0.0.0.0 \
    APP_PORT=8080 \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=80 \
    python pushi/src/pushi/base/state.py < /dev/null &> ~/pushi.log &

To be able to run in using SSL encryption additional commands must be used, please note
that the SSL port used by the app is not the default one:

    APP_SERVER=tornado \
    APP_HOST=0.0.0.0 \
    APP_PORT=9090 \
    APP_SSL=1 \
    APP_SSL_KEY=/path/to/file.key \
    APP_SSL_CER=/path/to/file.cer \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=443 \
    SERVER_SSL=1 \
    SERVER_SSL_KEY=/path/to/file.key \
    SERVER_SSL_CER=/path/to/file.cer \
    python pushi/src/pushi/base/state.py < /dev/null &> ~/pushi.log &

## Quick Start

```javascript
var pushi = new Pushi("YOU_APP_KEY");
pushi.bind("message", function(event, data) {
    jQuery("body").append("<div>" + data + "</div>");
});
```

```python
import pushi
    
pushi.trigger(
    channel = "global",
    data = "hello world",
    event = "message",
    app_id = "YOU_APP_ID",
    app_key = "YOU_APP_KEY",
    app_secret = "YOU_APP_SECRET"
)
```