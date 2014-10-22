# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import requests

from hm import config


_managers = {}
_expected_methods = ['create_host', 'destroy_host']


def register(name, cls):
    for m in _expected_methods:
        if not getattr(cls, m, None):
            raise InvalidManager("Expected method '{}' not found in {}".format(m, cls))
    _managers[name] = cls


def by_name(name, conf=None):
    return _managers[name](conf)


class BaseManager(object):
    def __init__(self, conf):
        self.config = conf or {}

    def get_conf(self, name, default=config.undefined):
        return config.get_config(name, default, self.config)

    def get_user_data(self):
        data = self.get_conf("USER_DATA_TXT", None)
        if data:
            return data
        url = self.get_conf("USER_DATA_URL", None)
        if not url:
            return None
        rsp = requests.get(url)
        if rsp.status_code < 200 or rsp.status_code >= 400:
            raise config.MissConfigurationError(
                "invalid user data response from {}: {} - {}".format(url, rsp.status_code, rsp.text))
        return rsp.text


class InvalidManager(Exception):
    pass
