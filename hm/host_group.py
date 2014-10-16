# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from hm import managers, log
from hm.storage import MongoDBStorage


class HostNotFoundError(Exception):
    def __init__(self, host, group):
        super(HostNotFoundError, self).__init__("host {} not found in group {}".format(host, group))


class HostGroup(object):
    def __init__(self, name):
        self.name = name
        self.storage = MongoDBStorage()

    def add_host(self, manager_name, conf=None):
        manager = managers.by_name(manager_name, conf)
        host = manager.create_host()
        host.manager = manager_name
        self.storage.add_host_to_group(self.name, host)
        return host

    def remove_host(self, host_id):
        host = self.storage.host_by_id_group(self.name, host_id)
        if host is None:
            raise HostNotFoundError(host_id, self.name)
        manager = managers.by_name(host.manager)
        try:
            manager.destroy_host(host.id)
        except Exception as e:
            log.error("Error trying to destroy host '{}' in '{}': {}".format(host.id, host.manager, e))
        self.storage.remove_host_from_group(self.name, host_id)

    def list_hosts(self):
        return self.storage.hosts_by_group(self.name)
