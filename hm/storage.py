# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import pymongo

from hm import config
from hm.model import host, load_balancer


class MongoDBStorage(object):
    hosts_collection = "hosts"
    lb_collection = "load_balancers"

    def __init__(self, conf=None):
        self.config = conf
        self.mongo_uri = config.get_config('DBAAS_MONGODB_ENDPOINT', None, conf)
        if not self.mongo_uri:
            self.mongo_uri = config.get_config('MONGO_URI', 'mongodb://localhost:27017/', conf)
        client = pymongo.MongoClient(self.mongo_uri)
        try:
            self.db = client.get_default_database()
            self.mongo_database = self.db.name
        except pymongo.errors.ConfigurationError:
            self.mongo_database = config.get_config('MONGO_DATABASE', 'host_manager', conf)
            self.db = client[self.mongo_database]

    def store_host(self, h):
        self._hosts_collection().insert(h.to_json())

    def remove_host(self, id):
        self._hosts_collection().remove({'_id': id})

    def find_host(self, id):
        h_data = self._hosts_collection().find_one({'_id': id})
        return host.Host.from_dict(h_data, conf=self.config)

    def list_hosts(self, filters):
        host_data_list = self._hosts_collection().find(filters) or []
        return [host.Host.from_dict(h_data, conf=self.config) for h_data in host_data_list]

    def store_load_balancer(self, lb):
        self._lb_collection().insert(lb.to_json())

    def remove_load_balancer(self, name):
        self._lb_collection().remove({'_id': name})

    def find_load_balancer(self, name):
        lb_data = self._lb_collection().find_one(name)
        return load_balancer.LoadBalancer.from_dict(lb_data, conf=self.config)

    def list_load_balancers(self, filters):
        lb_data_list = self._lb_collection().find(filters) or []
        return [load_balancer.LoadBalancer.from_dict(lb_data, conf=self.config) for lb_data in lb_data_list]

    def add_host_to_load_balancer(self, name, h):
        self._lb_collection().update({'_id': name}, {'$push': {'hosts': h.to_json()}})

    def remove_host_from_load_balancer(self, name, h):
        self._lb_collection().update({'_id': name}, {'$pull': {'hosts': {'_id': h.id}}})

    def _hosts_collection(self):
        return self.db[self.hosts_collection]

    def _lb_collection(self):
        return self.db[self.lb_collection]
