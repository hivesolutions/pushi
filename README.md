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

## Inspiration

Pushi was heavily inspired by the [Pusher](http://pusher.com) service, and aims
at providing a free alternative to it (for cost reducing).

## Quick Start

```javascript
var pushi = new Pushi("YOU_APP_KEY");
pushi.bind("message", function(event, data) {
    jQuery("body").append("<div>" + data + "</div>");
});
```