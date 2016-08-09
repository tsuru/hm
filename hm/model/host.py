# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import collections

from hm import managers, log, model, config


class Host(model.BaseModel):

    def __init__(self, id, dns_name, conf=None, alternative_id=0, **kwargs):
        self.id = id
        self.dns_name = dns_name
        self.manager = None
        self.extra_args = set()
        self.config = conf
        self.alternative_id = alternative_id
        for k, v in kwargs.items():
            self.extra_args.add(k)
            setattr(self, k, v)

    def to_json(self):
        obj = {
            '_id': self.id,
            'dns_name': self.dns_name,
            'manager': self.manager,
            'alternative_id': self.alternative_id,
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
        alternative_id = cls._current_group_alternate(group, conf)
        host = manager.create_host(name=group, alternative_id=alternative_id)
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

    def restore(self):
        manager = managers.by_name(self.manager, self.config)
        try:
            manager.restore_host(self.id)
        except Exception as e:
            log.error("Error trying to restore host '{}' in '{}': {}".format(self.id, self.manager, e))
            raise e

    def start(self):
        manager = managers.by_name(self.manager, self.config)
        try:
            manager.start_host(self.id)
        except Exception as e:
            log.error("Error trying to start host '{}' in '{}': {}".format(self.id, self.manager, e))
            raise e

    def stop(self, forced=False):
        manager = managers.by_name(self.manager, self.config)
        try:
            manager.stop_host(self.id, forced)
        except Exception as e:
            log.error("Error trying to stop host '{}' in '{}': {}".format(self.id, self.manager, e))
            raise e

    @classmethod
    def _current_group_alternate(cls, group, conf=None):
        alternates_count = int(config.get_config("HM_ALTERNATIVE_CONFIG_COUNT", 1, conf))
        hosts = model.storage(conf).list_hosts({'group': group})
        alterantives_map = collections.defaultdict(int)
        for host in hosts:
            alterantives_map[host.alternative_id] += 1
        min_alt_id = 0
        min_alt_count = None
        for i in xrange(alternates_count):
            if min_alt_count is None or alterantives_map[i] < min_alt_count:
                min_alt_id = i
                min_alt_count = alterantives_map[i]
        return min_alt_id
