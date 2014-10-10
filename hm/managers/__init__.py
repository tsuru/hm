# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import requests

from hm import config


_managers = {}


def register(name, cls):
    _managers[name] = cls


def by_name(name, conf=None):
    return _managers[name](conf)


class BaseManager(object):
    def __init__(self, conf):
        self.config = conf or {}

    def get_env(self, name, default=config.undefined):
        return config.get_config(name, self.config, default)

    def get_user_data(self):
        url = self.get_env("USER_DATA_URL", default=None)
        if not url:
            return None
        rsp = requests.get(url)
        if 200 <= rsp.status_code < 400:
            raise config.MissConfigurationError("invalid user data response from {}: {} - {}",
                                                url, rsp.status_code, rsp.data)
        return rsp.data
