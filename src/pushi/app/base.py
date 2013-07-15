#!/usr/bin/python
# -*- coding: utf-8 -*-

import appier

class PushiApp(appier.App):
    
    def __init__(self):
        appier.App(name = "pushi")

if __name__ == "__main__":
    app = PushiApp()
    app.serve()
