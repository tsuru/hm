# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import unittest

from hm import managers, host, storage
from hm.host_group import HostGroup, HostNotFoundError


class FakeManager(managers.BaseManager):
    def __init__(self, config=None):
        super(FakeManager, self).__init__(config)

    def create(self):
        host_id = self.get_env('HOST_ID')
        return host.Host(id=host_id, dns_name="{}.myhost.com".format(host_id))

    def destroy(self, id):
        if id == "explode":
            raise Exception("failure to destroy")

managers.register('fake', FakeManager)


class HostGroupTestCase(unittest.TestCase):

    def setUp(self):
        mongo_stor = storage.MongoDBStorage()
        mongo_stor._collection().remove()

    def test_init(self):
        hg = HostGroup("my-group")
        self.assertEqual(hg.name, "my-group")

    def test_add_host(self):
        hg = HostGroup("my-group")
        host = hg.add_host('fake', {"HOST_ID": "fake-id"})
        self.assertEqual(host.id, "fake-id")
        self.assertEqual(host.dns_name, "fake-id.myhost.com")
        self.assertEqual(host.manager, "fake")
        hosts = hg.list_hosts()
        self.assertEqual(len(hosts), 1)
        self.assertEqual(hosts[0].id, host.id)
        self.assertEqual(hosts[0].dns_name, host.dns_name)
        self.assertEqual(hosts[0].manager, host.manager)

    def test_remove_host(self):
        hg = HostGroup("my-group")
        host = hg.add_host('fake', {"HOST_ID": "fake-id"})
        self.assertEqual(host.id, "fake-id")
        hosts = hg.list_hosts()
        self.assertEqual(len(hosts), 1)
        hg.remove_host('fake-id')
        hosts = hg.list_hosts()
        self.assertEqual(len(hosts), 0)

    def test_remove_host_error(self):
        hg = HostGroup("my-group")
        with self.assertRaises(HostNotFoundError):
            hg.remove_host('to-error')
        hg2 = HostGroup("my-group-2")
        hg2.add_host('fake', {"HOST_ID": "group-2-host"})
        with self.assertRaises(HostNotFoundError):
            hg.remove_host('group-2-host')

    def test_remove_host_ignore_manager_error(self):
        hg = HostGroup("my-group")
        host = hg.add_host('fake', {"HOST_ID": "explode"})
        hg.remove_host(host.id)
        hosts = hg.list_hosts()
        self.assertEqual(len(hosts), 0)
