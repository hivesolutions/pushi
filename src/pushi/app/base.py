#!/usr/bin/python
# -*- coding: utf-8 -*-

import appier

class PushiApp(appier.App):

    def __init__(self):
        appier.App.__init__(self, name = "pushi")

    @appier.route("^/api/hello$")
    def tobias(self):
        return dict(message = "hello world")

if __name__ == "__main__":
    app = PushiApp()
    app.serve()
