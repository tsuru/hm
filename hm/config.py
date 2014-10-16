# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import os


undefined = object()


def get_config(name, default=undefined, config=None):
    try:
        value = (config or {}).get(name)
        if value is None:
            value = os.environ[name]
        return value
    except KeyError:
        if default is not undefined:
            return default
        raise MissConfigurationError("env var {} is required".format(name))


class MissConfigurationError(Exception):
    pass
