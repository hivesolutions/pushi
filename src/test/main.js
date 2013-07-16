jQuery(document).ready(function() {
            var pushi = new Pushi("app_key");
            pushi.bind("message", function(event, data) {
                        jQuery("body").append("<div>" + data + "</div>");
                    });
        });
