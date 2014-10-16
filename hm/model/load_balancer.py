# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.


class LoadBalancer(object):
    def __init__(self, id, name, address, **kwargs):
        self.id = id
        self.address = address
        self.manager = None
        self.extra_args = set()
        for k, v in kwargs.items():
            self.extra_args.add(k)
            self.__setattr__(k, v)

    def to_json(self):
        obj = {
            'id': self.id,
            'address': self.address,
            'manager': self.manager,
        }
        for key in self.extra_args:
            obj[key] = self.__getattr__(key)
        return obj
