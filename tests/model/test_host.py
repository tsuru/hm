# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import unittest

from hm import managers, storage
from hm.model.host import Host


class FakeManager(managers.BaseManager):
    def __init__(self, config=None):
        super(FakeManager, self).__init__(config)

    def create_host(self):
        host_id = self.get_conf('HOST_ID')
        return Host(id=host_id, dns_name="{}.myhost.com".format(host_id))

    def destroy_host(self, id):
        if id == "explode":
            raise Exception("failure to destroy")

managers.register('fake', FakeManager)


class HostTestCase(unittest.TestCase):

    def setUp(self):
        mongo_stor = storage.MongoDBStorage()
        mongo_stor._hosts_collection().remove()

    def test_create(self):
        host = Host.create('fake', 'my-group', {"HOST_ID": "fake-id"})
        self.assertEqual(host.id, "fake-id")
        self.assertEqual(host.dns_name, "fake-id.myhost.com")
        self.assertEqual(host.manager, "fake")
        self.assertEqual(host.group, "my-group")
        db_host = Host.find('fake-id')
        self.assertEqual(db_host.id, "fake-id")
        self.assertEqual(db_host.dns_name, "fake-id.myhost.com")
        self.assertEqual(db_host.manager, "fake")
        self.assertEqual(db_host.group, "my-group")

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
        hosts = Host.list()
        self.assertItemsEqual([h.to_json() for h in hosts], [h1.to_json(), h2.to_json(), h3.to_json()])
        hosts = Host.list({'group': 'my-group1'})
        self.assertItemsEqual([h.to_json() for h in hosts], [h1.to_json(), h2.to_json()])
