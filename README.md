# Pushi Websockets

Simple yet powerfull infra-structure for handling of websocket connection.

## Quick Start

    var pushi = new Pushi("YOU_APP_KEY");
    pushi.bind("message", function(event, data) {
        jQuery("body").append("<div>" + data + "</div>");
    });
