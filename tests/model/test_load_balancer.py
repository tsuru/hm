# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import unittest

import pymongo.errors

from hm import lb_managers, storage
from hm.model.host import Host
from hm.model.load_balancer import LoadBalancer
from mock import patch, call


class FakeManager(lb_managers.BaseLBManager):
    def __init__(self, config=None):
        super(FakeManager, self).__init__(config)

    def create_load_balancer(self, name):
        id = self.get_conf('LB_ID')
        return LoadBalancer(id, name, 'xxx.host', extra='something')

    def destroy_load_balancer(self, lb):
        if lb.id == "explode":
            raise Exception("failure to destroy")

    def attach_real(self, lb, host):
        pass

    def detach_real(self, lb, host):
        pass

lb_managers.register('fake', FakeManager)


class LoadBalancerTestCase(unittest.TestCase):

    def setUp(self):
        mongo_stor = storage.MongoDBStorage()
        mongo_stor._lb_collection().remove()

    def test_create(self):
        conf = {'LB_ID': 'xxx'}
        lb = LoadBalancer.create('fake', 'my-lb', conf=conf)
        self.assertEqual(lb.id, 'xxx')
        self.assertEqual(lb.name, 'my-lb')
        self.assertEqual(lb.manager, 'fake')
        self.assertEqual(lb.extra, 'something')
        self.assertEqual(lb.config, conf)
        db_lb = LoadBalancer.find('my-lb', conf=conf)
        self.assertEqual(db_lb.id, 'xxx')
        self.assertEqual(db_lb.name, 'my-lb')
        self.assertEqual(db_lb.manager, 'fake')
        self.assertEqual(db_lb.extra, 'something')
        self.assertEqual(db_lb.config, conf)

    def test_create_duplicated(self):
        lb = LoadBalancer.create('fake', 'my-lb', {'LB_ID': 'xxx'})
        self.assertEqual(lb.id, 'xxx')
        self.assertEqual(lb.name, 'my-lb')
        with self.assertRaises(pymongo.errors.DuplicateKeyError):
            LoadBalancer.create('fake', 'my-lb', {'LB_ID': 'xxx'})

    def test_destroy(self):
        LoadBalancer.create('fake', 'my-lb', {'LB_ID': 'xxx'})
        db_lb = LoadBalancer.find('my-lb')
        self.assertEqual(db_lb.id, 'xxx')
        db_lb.destroy()
        db_lb = LoadBalancer.find('my-lb')
        self.assertIsNone(db_lb)

    @patch("hm.log.error")
    def test_destroy_ignores_manager_exception(self, log):
        LoadBalancer.create('fake', 'my-lb', {'LB_ID': 'explode'})
        db_lb = LoadBalancer.find('my-lb')
        self.assertEqual(db_lb.id, 'explode')
        db_lb.destroy()
        self.assertEqual(log.call_args, call("Error trying to destroy load balancer name: 'my-lb' "
                                             "id: 'explode' in 'fake': failure to destroy"))
        db_lb = LoadBalancer.find('my-lb')
        self.assertIsNone(db_lb)

    def test_add_host(self):
        h1 = Host('x', 'x.me.com')
        h2 = Host('y', 'y.me.com')
        conf = {'LB_ID': 'explode'}
        lb = LoadBalancer.create('fake', 'my-lb', conf)
        lb.add_host(h1)
        lb.add_host(h2)
        self.assertItemsEqual(lb.hosts, [h1, h2])
        db_lb = LoadBalancer.find('my-lb', conf)
        self.assertEqual(db_lb.hosts[0].config, conf)
        self.assertEqual(db_lb.hosts[1].config, conf)
        self.assertItemsEqual([h.to_json() for h in db_lb.hosts], [h1.to_json(), h2.to_json()])

    def test_remove_host(self):
        h1 = Host('x', 'x.me.com')
        h2 = Host('y', 'y.me.com')
        lb = LoadBalancer.create('fake', 'my-lb', {'LB_ID': 'explode'})
        lb.add_host(h1)
        lb.add_host(h2)
        lb.remove_host(h1)
        self.assertItemsEqual(lb.hosts, [h2])
        db_lb = LoadBalancer.find('my-lb')
        self.assertItemsEqual([h.to_json() for h in db_lb.hosts], [h2.to_json()])
