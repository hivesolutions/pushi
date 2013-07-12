jQuery(document).ready(function() {
            var socket = new WebSocket("ws://localhost:9090/");
            socket.onopen = function() {
                socket.send("Hello World");
                console.info("Message is sent...");
            };

            socket.onmessage = function(event) {
                var message = event.data;
                console.info("Message is received '" +  message + "'...");
            };

            socket.onclose = function() {
                // websocket is closed.
                console.info("Connection is closed...");
            };
        });
