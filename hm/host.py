# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.


def from_dict(dict):
    host = Host(dict['id'], dict['dns_name'])
    host.manager = dict['manager']
    return host


class Host(object):
    def __init__(self, id, dns_name):
        self.id = id
        self.dns_name = dns_name
        self.manager = None

    def to_json(self):
        return {
            'id': self.id,
            'dns_name': self.dns_name,
            'manager': self.manager,
        }
