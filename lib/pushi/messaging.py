#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Pushi System
# Copyright (c) 2008-2024 Hive Solutions Lda.
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

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """


class MessagingAPI(object):
    def send_messaging(self, adapters, data=None, **kwargs):
        # creates the initial JSON data structure to be used as the message
        # and then "extends" it with the extra key word arguments passed
        # to this method as a method of extension
        data_j = dict(adapters=adapters, data=data)
        for key in kwargs:
            data_j[key] = kwargs[key]

        # performs the concrete direct messaging operation sending the
        # message through the provided adapters using the currently
        # defined app id, then returns the resulting dictionary
        result = self.post(self.base_url + "messaging/send", data_j=data_j)
        return result

    def send_messaging_apn(self, tokens, message, **kwargs):
        # creates the initial JSON data structure to be used as the message
        # and then "extends" it with the extra key word arguments passed
        # to this method as a method of extension
        data_j = dict(tokens=tokens, message=message)
        for key in kwargs:
            data_j[key] = kwargs[key]

        # performs the concrete APN direct messaging operation sending the
        # notification to the provided tokens using the currently defined
        # app id, then returns the resulting dictionary to the caller method
        result = self.post(self.base_url + "messaging/apn", data_j=data_j)
        return result

    def send_messaging_email(self, to, subject, body, **kwargs):
        # creates the initial JSON data structure to be used as the message
        # and then "extends" it with the extra key word arguments passed
        # to this method as a method of extension
        data_j = dict(to=to, subject=subject, body=body)
        for key in kwargs:
            data_j[key] = kwargs[key]

        # performs the concrete email direct messaging operation sending the
        # email to the provided recipients using the currently defined app
        # id, then returns the resulting dictionary to the caller method
        result = self.post(self.base_url + "messaging/email", data_j=data_j)
        return result

    def send_messaging_webhook(self, urls, data, **kwargs):
        # creates the initial JSON data structure to be used as the message
        # and then "extends" it with the extra key word arguments passed
        # to this method as a method of extension
        data_j = dict(urls=urls, data=data)
        for key in kwargs:
            data_j[key] = kwargs[key]

        # performs the concrete webhook direct messaging operation sending the
        # HTTP request to the provided URLs, this operation does not require
        # an app id, then returns the resulting dictionary to the caller method
        result = self.post(self.base_url + "messaging/webhook", data_j=data_j)
        return result

    def send_messaging_web_push(self, message=None, **kwargs):
        # creates the initial JSON data structure to be used as the message
        # and then "extends" it with the extra key word arguments passed
        # to this method as a method of extension
        data_j = dict(message=message)
        for key in kwargs:
            data_j[key] = kwargs[key]

        # performs the concrete Web Push direct messaging operation sending the
        # notification to the provided subscriptions using the currently
        # defined app id, then returns the resulting dictionary
        result = self.post(self.base_url + "messaging/web_push", data_j=data_j)
        return result
