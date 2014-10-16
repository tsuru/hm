# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from hm import config


_managers = {}
_expected_methods = ['create_load_balancer', 'destroy_load_balancer', 'attach_real', 'detach_real']


def register(name, cls):
    for m in _expected_methods:
        if not getattr(cls, m, None):
            raise InvalidLBManager("Expected method '{}' not found in {}".format(m, cls))
    _managers[name] = cls


def by_name(name, conf=None):
    return _managers[name](conf)


class BaseLBManager(object):
    def __init__(self, conf):
        self.config = conf or {}

    def get_conf(self, name, default=config.undefined):
        return config.get_config(name, default, self.config)


class LBConfig(object):
    environment_p44 = None
    client = None
    finality = None
    healthcheck = None
    healthcheck_expect = None
    cache = None
    lb_method = None
    persistence = None
    maxconn = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            self.__setattr__(k, v)


class InvalidLBManager(Exception):
    pass
