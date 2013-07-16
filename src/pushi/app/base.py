#!/usr/bin/python
# -*- coding: utf-8 -*-

import appier

class PushiApp(appier.App):

    def __init__(self, state):
        appier.App.__init__(self, name = "pushi")
        self.state = state

    @appier.route("/hello/<message>")
    def hello(self, message):
        message = "hello world %s" % message
        return dict(message = message.strip())

    @appier.route("/apps/<app_id>/events", "POST")
    def event(self, app_id, data):
        print app_id
        print data

    @appier.route("/tobias", "GET")
    def tobias(self):
        self.state.send_channel("global", {"tobias" : "lider"})

if __name__ == "__main__":
    app = PushiApp()
    app.serve()
