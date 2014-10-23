# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from hm import lb_managers, log, model
from hm.model.host import Host


class LoadBalancer(model.BaseModel):

    def __init__(self, id, name, address, conf=None, **kwargs):
        self.id = id
        self.name = name
        self.address = address
        self.manager = None
        self.extra_args = set()
        self.config = conf
        self.hosts = []
        for k, v in kwargs.items():
            self.extra_args.add(k)
            setattr(self, k, v)

    def to_json(self):
        obj = {
            '_id': self.name,
            'id': self.id,
            'address': self.address,
            'manager': self.manager,
        }
        for key in self.extra_args:
            obj[key] = getattr(self, key)
        return obj

    @classmethod
    def from_dict(cls, dict, conf=None):
        if dict is None:
            return None
        dict['name'] = dict['_id']
        del dict['_id']
        dict['conf'] = conf
        hosts_data = dict.get('hosts', None)
        if hosts_data:
            dict['hosts'] = [Host.from_dict(h, conf=conf) for h in hosts_data]
        return cls(**dict)

    @classmethod
    def create(cls, manager_name, name, conf=None):
        manager = lb_managers.by_name(manager_name, conf)
        lb = manager.create_load_balancer(name)
        lb.manager = manager_name
        lb.config = conf
        model.storage(conf).store_load_balancer(lb)
        return lb

    @classmethod
    def find(cls, name, conf=None):
        return model.storage(conf).find_load_balancer(name)

    @classmethod
    def list(cls, filters=None, conf=None):
        return model.storage(conf).list_load_balancers(filters)

    def destroy(self):
        manager = self._manager()
        try:
            manager.destroy_load_balancer(self)
        except Exception as e:
            log.error("Error trying to destroy load balancer name: '{}' id: '{}' in '{}': {}".format(
                self.name, self.id, self.manager, e))
        self.storage().remove_load_balancer(self.name)

    def add_host(self, host):
        manager = self._manager()
        manager.attach_real(self, host)
        self.storage().add_host_to_load_balancer(self.name, host)
        self.hosts.append(host)

    def remove_host(self, host):
        manager = self._manager()
        manager.detach_real(self, host)
        self.storage().remove_host_from_load_balancer(self.name, host)
        self.hosts = [h for h in self.hosts if h.id != host.id]

    def _manager(self):
        return lb_managers.by_name(self.manager, self.config)
