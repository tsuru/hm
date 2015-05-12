# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import logging


_log = logging.getLogger('tsuru.hm')


def debug(*args):
    _log.debug(*args)


def error(*args):
    _log.error(*args)


def exception(*args):
    _log.exception(*args)


def set_handler(handler):
    _log.removeHandler(_default_handler)
    _log.addHandler(handler)

_default_handler = logging.StreamHandler()
_default_handler.setLevel(logging.INFO)
_log.addHandler(_default_handler)
