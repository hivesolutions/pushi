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

## Running

To be able to run the pushi infra-structure under a normal non ecrypted connection
and bind to the complete set of network interfaces in the host the following command:

    APP_HOST=0.0.0.0 \
    APP_PORT=8080 \
    SERVER_HOST=0.0.0.0 \
    SERVER_PORT=80 \
    python pushi/src/pushi/base/state.py < /dev/null &> ~/pushi.log &

To be able to run in using SSL encryption additional commands must be used:

    APP_HOST=0.0.0.0 \
    APP_PORT=80 \
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