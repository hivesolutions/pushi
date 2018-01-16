#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (c) 2008-2018 Hive Solutions Lda.
#
# This file is part of Hive Pushi System.
#
# Hive Pushi System is free software: you can redistribute it and/or modify
# it under the terms of the Apache License as published by the Apache
# Foundation, either version 2.0 of the License, or (at your option) any
# later version.
#
# Hive Pushi System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# Apache License for more details.
#
# You should have received a copy of the Apache License along with
# Hive Pushi System. If not, see <http://www.apache.org/licenses/>.

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__version__ = "1.0.0"
""" The version of the module """

__revision__ = "$LastChangedRevision$"
""" The revision number of the module """

__date__ = "$LastChangedDate$"
""" The last change date of the module """

__copyright__ = "Copyright (c) 2008-2018 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

class EventAPI(object):

    def create_event(self, channel, data, event = "message", persist = True, **kwargs):
        # creates the initial json data structure to be used as the message
        # and then "extends" it with the extra key word arguments passed
        # to this methods as a method of extension
        data_j = dict(
            data = data,
            event = event,
            channel = channel,
            persist = persist
        )
        for key in kwargs: data_j[key] = kwargs[key]

        # performs the concrete event trigger operation creating an event
        # with the provided information using a secure channel
        result = self.post(
            self.base_url + "events",
            data_j = data_j
        )
        return result

    def trigger_event(self, *args, **kwargs):
        return self.create_event(*args, **kwargs)
