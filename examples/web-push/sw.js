// Hive Pushi System
// Copyright (c) 2008-2024 Hive Solutions Lda.
//
// This file is part of Hive Pushi System.
//
// Hive Pushi System is free software: you can redistribute it and/or modify
// it under the terms of the Apache License as published by the Apache
// Foundation, either version 2.0 of the License, or (at your option) any
// later version.
//
// Hive Pushi System is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
// Apache License for more details.
//
// You should have received a copy of the Apache License along with
// Hive Pushi System. If not, see <http://www.apache.org/licenses/>.

// __author__    = João Magalhães <joamag@hive.pt>
// __copyright__ = Copyright (c) 2008-2024 Hive Solutions Lda.
// __license__   = Apache License, Version 2.0

// default icon for notifications (can be overridden in payload)
var DEFAULT_ICON = "icon.svg";

// default vibration pattern: short-pause-short-pause-long
var DEFAULT_VIBRATE = [200, 100, 200, 100, 400];

// handles the push event triggered when a notification
// is received from the push service, parses the payload
// and displays the notification to the user
self.addEventListener("push", function(event) {
    var data = event.data ? event.data.json() : {};
    var title = data.title || "Notification";
    var options = {
        body: data.body || data.message || "",
        icon: data.icon || DEFAULT_ICON,
        badge: data.badge,
        image: data.image,
        vibrate: data.vibrate || DEFAULT_VIBRATE,
        tag: data.tag,
        renotify: data.renotify || false,
        requireInteraction: data.requireInteraction || false,
        silent: data.silent || false,
        actions: data.actions,
        data: data
    };

    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

// handles clicks on the notification, closes it and
// optionally opens a URL if one was provided in the
// notification payload data
self.addEventListener("notificationclick", function(event) {
    event.notification.close();

    var data = event.notification.data || {};
    var action = event.action;

    // handles specific action buttons if clicked
    if (action === "dismiss") {
        return;
    }

    // opens URL from action or default notification URL
    var url = data.url;
    if (action && data.actions) {
        var actionData = data.actions.find(function(a) {
            return a.action === action;
        });
        if (actionData && actionData.url) {
            url = actionData.url;
        }
    }

    if (url) {
        event.waitUntil(clients.openWindow(url));
    }
});
