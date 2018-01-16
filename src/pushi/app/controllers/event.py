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

import appier

import pushi

class EventController(appier.Controller):

    @appier.private
    @appier.route("/events", "GET")
    def list(self):
        count = self.field("count", 10, cast = int)
        events = pushi.PushiEvent.find(
            limit = count,
            sort = [("_id", -1),],
            map = True
        )
        return dict(
            events = events
        )

    @appier.private
    @appier.route("/events", "POST")
    def create(self):
        data = self.request.get_json() or dict()
        app_id = self.session.get("app_id", None)
        _data = data.get("data", None)
        event = data.get("event", "message")
        channel = data.get("channel", "global")
        persist = data.get("persist", True)
        if not _data: raise RuntimeError("No data set for event")
        self.state.trigger(
            app_id,
            event,
            _data,
            channels = channel,
            persist = persist,
            json_d = data,
            verify = False
        )
