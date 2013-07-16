# Pushi Websockets

Simple yet powerfull infra-structure for handling of websocket connection.

## Inspiration

Pushi was heavily inspired by the [Pusher](http://pusher.com) service, and aims
at providing a free alternative to it (for cost reducing).

## Quick Start

    var pushi = new Pushi("YOU_APP_KEY");
    pushi.bind("message", function(event, data) {
        jQuery("body").append("<div>" + data + "</div>");
    });
