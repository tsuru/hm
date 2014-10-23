# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import unittest

from hm import managers, storage
from hm.model.host import Host


class FakeManager(managers.BaseManager):
    def __init__(self, config=None):
        super(FakeManager, self).__init__(config)

    def create_host(self, name=None):
        host_id = self.get_conf('HOST_ID')
        return Host(id=host_id, dns_name="{}.{}.com".format(host_id, name))

    def destroy_host(self, id):
        if id == "explode":
            raise Exception("failure to destroy")

managers.register('fake', FakeManager)


class HostTestCase(unittest.TestCase):

    def setUp(self):
        storage.MongoDBStorage()._hosts_collection().remove()

    def test_create(self):
        conf = {"HOST_ID": "fake-id"}
        host = Host.create('fake', 'my-group', conf)
        self.assertEqual(host.id, "fake-id")
        self.assertEqual(host.dns_name, "fake-id.my-group.com")
        self.assertEqual(host.manager, "fake")
        self.assertEqual(host.group, "my-group")
        self.assertEqual(host.config, conf)
        db_host = Host.find('fake-id', conf=conf)
        self.assertEqual(db_host.id, "fake-id")
        self.assertEqual(db_host.dns_name, "fake-id.my-group.com")
        self.assertEqual(db_host.manager, "fake")
        self.assertEqual(db_host.group, "my-group")
        self.assertEqual(db_host.config, conf)

    def test_destroy(self):
        host = Host.create('fake', 'my-group', {"HOST_ID": "fake-id"})
        self.assertEqual(host.id, "fake-id")
        host.destroy()
        db_host = Host.find('fake-id')
        self.assertIsNone(db_host)

    def test_destroy_ignores_manager_error(self):
        host = Host.create('fake', 'my-group', {"HOST_ID": "explode"})
        self.assertEqual(host.id, "explode")
        host.destroy()
        db_host = Host.find('explode')
        self.assertIsNone(db_host)

    def test_list(self):
        h1 = Host.create('fake', 'my-group1', {"HOST_ID": "fake-id-1"})
        h2 = Host.create('fake', 'my-group1', {"HOST_ID": "fake-id-2"})
        h3 = Host.create('fake', 'my-group2', {"HOST_ID": "fake-id-3"})
        conf = {'MY_CONF': 1}
        hosts = Host.list(conf=conf)
        self.assertDictEqual(hosts[0].config, conf)
        self.assertDictEqual(hosts[1].config, conf)
        self.assertDictEqual(hosts[2].config, conf)
        self.assertItemsEqual([h.to_json() for h in hosts], [h1.to_json(), h2.to_json(), h3.to_json()])
        hosts = Host.list({'group': 'my-group1'})
        self.assertItemsEqual([h.to_json() for h in hosts], [h1.to_json(), h2.to_json()])

    def test_storage_use_conf(self):
        storage.MongoDBStorage({"MONGO_DATABASE": "alternative_host_manager"})._hosts_collection().remove()
        h1 = Host.create('fake', 'my-group1', {
            "HOST_ID": "fake-id-x", "MONGO_DATABASE": "alternative_host_manager"
        })
        stor = h1.storage()
        self.assertEqual(stor.mongo_database, "alternative_host_manager")
        h1.destroy()
        db_host = Host.find('fake-id-x')
        self.assertIsNone(db_host)
