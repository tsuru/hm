# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import pymongo

from hm import config, host


class MongoDBStorage(object):

    def __init__(self, conf=None):
        self.mongo_uri = config.get_config('MONGO_URI', conf, 'mongodb://localhost:27017/')
        self.mongo_database = config.get_config('MONGO_DATABASE', conf, 'host_manager')
        client = pymongo.MongoClient(self.mongo_uri)
        self.db = client[self.mongo_database]
        self.collection_name = "instances"

    def add_host_to_group(self, group_name, host):
        self._collection().update(
            {'_id': group_name},
            {'$addToSet': {'hosts': host.to_json()}},
            upsert=True
        )

    def remove_host_from_group(self, group_name, host_id):
        self._collection().update(
            {'_id': group_name},
            {'$pull': {'hosts': {'id': host_id}}},
        )

    def host_by_id_group(self, group_name, host_id):
        group = self._collection().find_one({'_id': group_name, 'hosts.id': host_id})
        if not group:
            return None
        for h in group['hosts']:
            if h['id'] == host_id:
                return host.from_dict(h)
        return None

    def hosts_by_group(self, group_name):
        group = self._collection().find_one(group_name)
        return [host.from_dict(h) for h in group['hosts']]

    def _collection(self):
        return self.db[self.collection_name]
