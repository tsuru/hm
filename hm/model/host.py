# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from hm import managers, log, model


class Host(model.BaseModel):

    def __init__(self, id, dns_name, conf=None, **kwargs):
        self.id = id
        self.dns_name = dns_name
        self.manager = None
        self.extra_args = set()
        self.config = conf
        for k, v in kwargs.items():
            self.extra_args.add(k)
            setattr(self, k, v)

    def to_json(self):
        obj = {
            '_id': self.id,
            'dns_name': self.dns_name,
            'manager': self.manager,
            'group': getattr(self, 'group', None),
        }
        for key in self.extra_args:
            obj[key] = getattr(self, key)
        return obj

    @classmethod
    def from_dict(cls, dict, conf=None):
        if dict is None:
            return None
        dict['id'] = dict['_id']
        del dict['_id']
        dict['conf'] = conf
        return Host(**dict)

    @classmethod
    def create(cls, manager_name, group, conf=None):
        manager = managers.by_name(manager_name, conf)
        host = manager.create_host()
        host.manager = manager_name
        host.group = group
        host.config = conf
        model.storage(conf).store_host(host)
        return host

    @classmethod
    def find(cls, id, conf=None):
        return model.storage(conf).find_host(id)

    @classmethod
    def list(cls, filters=None, conf=None):
        return model.storage(conf).list_hosts(filters)

    def destroy(self):
        manager = managers.by_name(self.manager, self.config)
        try:
            manager.destroy_host(self.id)
        except Exception as e:
            log.error("Error trying to destroy host '{}' in '{}': {}".format(self.id, self.manager, e))
        self.storage().remove_host(self.id)
