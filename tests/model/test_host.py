# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import unittest

from hm import managers, storage
from hm.model.host import Host
from mock import patch, call


class FakeManager(managers.BaseManager):
    def __init__(self, config=None):
        super(FakeManager, self).__init__(config)

    def create_host(self, name=None, alternative_id=0):
        host_id = self.get_conf('HOST_ID')
        return Host(id=host_id, dns_name="{}.{}.com".format(host_id, name), alternative_id=alternative_id)

    def destroy_host(self, id):
        if id == "explode":
            raise Exception("failure to destroy")

    def restore_host(self, id):
        if id == "explode":
            raise Exception("failure to restore")

    def stop_host(self, id, forced=False):
        if id == "explode":
            raise Exception("failure to stop")

    def start_host(self, id):
        if id == "explode":
            raise Exception("failure to start")


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
        self.assertEqual(host.alternative_id, 0)
        db_host = Host.find('fake-id', conf=conf)
        self.assertEqual(db_host.id, "fake-id")
        self.assertEqual(db_host.dns_name, "fake-id.my-group.com")
        self.assertEqual(db_host.manager, "fake")
        self.assertEqual(db_host.group, "my-group")
        self.assertEqual(db_host.config, conf)
        self.assertEqual(db_host.alternative_id, 0)

    def test_create_alternatives(self):
        conf = {"HM_ALTERNATIVE_CONFIG_COUNT": "3"}
        conf.update({"HOST_ID": "fake-1"})
        host = Host.create('fake', 'my-group', conf)
        self.assertEqual(host.alternative_id, 0)
        conf.update({"HOST_ID": "fake-2"})
        host = Host.create('fake', 'my-group', conf)
        self.assertEqual(host.alternative_id, 1)
        conf.update({"HOST_ID": "fake-3"})
        host = Host.create('fake', 'my-group', conf)
        self.assertEqual(host.alternative_id, 2)
        conf.update({"HOST_ID": "fake-4"})
        host = Host.create('fake', 'my-group', conf)
        self.assertEqual(host.alternative_id, 0)
        conf.update({"HOST_ID": "fake-5"})
        host = Host.create('fake', 'my-group', conf)
        self.assertEqual(host.alternative_id, 1)
        conf.update({"HOST_ID": "fake-6"})
        host = Host.create('fake', 'another-group', conf)
        self.assertEqual(host.alternative_id, 0)
        hosts = Host.list(filters={'alternative_id': 0})
        self.assertEqual(len(hosts), 3)
        hosts = Host.list(filters={'alternative_id': 1})
        self.assertEqual(len(hosts), 2)
        hosts = Host.list(filters={'alternative_id': 2})
        self.assertEqual(len(hosts), 1)

    def test_destroy(self):
        host = Host.create('fake', 'my-group', {"HOST_ID": "fake-id"})
        self.assertEqual(host.id, "fake-id")
        host.destroy()
        db_host = Host.find('fake-id')
        self.assertIsNone(db_host)

    @patch("hm.log.error")
    def test_destroy_ignores_manager_error(self, log):
        host = Host.create('fake', 'my-group', {"HOST_ID": "explode"})
        self.assertEqual(host.id, "explode")
        host.destroy()
        self.assertEqual(log.call_args, call("Error trying to destroy host 'explode' "
                                             "in 'fake': failure to destroy"))
        db_host = Host.find('explode')
        self.assertIsNone(db_host)

    def test_restore(self):
        host = Host.create('fake', 'my-group', {"HOST_ID": "fake-id"})
        self.assertEqual(host.id, "fake-id")
        host.restore()

    @patch("hm.log.error")
    def test_restore_log_and_raises_exception_on_error(self, log):
        host = Host.create('fake', 'my-group', {"HOST_ID": "explode"})
        self.assertEqual(host.id, "explode")
        self.assertRaises(Exception, host.restore)
        self.assertEqual(log.call_args, call("Error trying to restore host 'explode' "
                                             "in 'fake': failure to restore"))
        db_host = Host.find('explode')
        self.assertEqual(db_host.id, "explode")

    def test_stop(self):
        host = Host.create('fake', 'my-group', {"HOST_ID": "fake-id"})
        self.assertEqual(host.id, "fake-id")
        host.stop()

    @patch("hm.log.error")
    def test_stop_log_and_raises_exception_on_error(self, log):
        host = Host.create('fake', 'my-group', {"HOST_ID": "explode"})
        self.assertEqual(host.id, "explode")
        self.assertRaises(Exception, host.stop)
        self.assertEqual(log.call_args, call("Error trying to stop host 'explode' "
                                             "in 'fake': failure to stop"))
        db_host = Host.find('explode')
        self.assertEqual(db_host.id, "explode")

    def test_start(self):
        host = Host.create('fake', 'my-group', {"HOST_ID": "fake-id"})
        self.assertEqual(host.id, "fake-id")
        host.start()

    @patch("hm.log.error")
    def test_start_log_and_raises_exception_on_error(self, log):
        host = Host.create('fake', 'my-group', {"HOST_ID": "explode"})
        self.assertEqual(host.id, "explode")
        self.assertRaises(Exception, host.start)
        self.assertEqual(log.call_args, call("Error trying to start host 'explode' "
                                             "in 'fake': failure to start"))
        db_host = Host.find('explode')
        self.assertEqual(db_host.id, "explode")

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

    def test_storage_use_database_conf(self):
        storage.MongoDBStorage({"MONGO_DATABASE": "alternative_host_manager"})._hosts_collection().remove()
        h1 = Host.create('fake', 'my-group1', {
            "HOST_ID": "fake-id-x", "MONGO_DATABASE": "alternative_host_manager"
        })
        stor = h1.storage()
        self.assertEqual(stor.mongo_database, "alternative_host_manager")
        self.assertEqual(stor.db.name, "alternative_host_manager")
        h1.destroy()
        db_host = Host.find('fake-id-x')
        self.assertIsNone(db_host)

    def test_storage_use_uri_conf(self):
        conf = {
            "DBAAS_MONGODB_ENDPOINT": "mongodb://127.0.0.1:27017/some_other_db",
            "MONGO_URI": "mongodb://127.0.0.1:27017/ignored",
        }
        storage.MongoDBStorage(conf)._hosts_collection().remove()
        host_config = {
            "HOST_ID": "fake-id-x"
        }
        host_config.update(conf)
        h1 = Host.create('fake', 'my-group1', host_config)
        stor = h1.storage()
        self.assertEqual(stor.mongo_database, "some_other_db")
        self.assertEqual(stor.db.name, "some_other_db")
        h1.destroy()
        db_host = Host.find('fake-id-x')
        self.assertIsNone(db_host)
        conf = {
            "MONGO_URI": "mongodb://127.0.0.1:27017/now_used",
        }
        storage.MongoDBStorage(conf)._hosts_collection().remove()
        host_config = {
            "HOST_ID": "fake-id-x"
        }
        host_config.update(conf)
        h1 = Host.create('fake', 'my-group1', host_config)
        stor = h1.storage()
        self.assertEqual(stor.mongo_database, "now_used")
        self.assertEqual(stor.db.name, "now_used")
        h1.destroy()
        db_host = Host.find('fake-id-x')
        self.assertIsNone(db_host)
