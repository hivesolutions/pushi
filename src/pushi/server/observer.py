#!/usr/bin/python
# -*- coding: utf-8 -*-

class Observable(object):

    def __init__(self, *args, **kwargs):
        self.events = {}

    def bind(self, name, method):
        methods = self.events.get(name, [])
        methods.append(method)
        self.events[name] = methods

    def unbind(self, name, method = None):
        methods = self.events.get(name, [])
        if method: methods.remove(method)
        else: methods[:] = []

    def trigger(self, name, *args, **kwargs):
        methods = self.events.get(name, [])
        for method in methods: method(*args, **kwargs)
