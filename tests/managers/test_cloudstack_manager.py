# Copyright 2015 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import unittest

import mock

from hm import config
from hm.managers import cloudstack
from hm.iaas import cloudstack_client


class CloudStackManagerTestCase(unittest.TestCase):

    def setUp(self):
        self.config = {
            "CLOUDSTACK_API_URL": "http://cloudstackapi",
            "CLOUDSTACK_API_KEY": "key",
            "CLOUDSTACK_SECRET_KEY": "secret",
        }

    def test_init(self):
        client = cloudstack.CloudStackManager(self.config)
        self.assertEqual(client.client.api_url, self.config["CLOUDSTACK_API_URL"])
        self.assertEqual(client.client.api_key, self.config["CLOUDSTACK_API_KEY"])
        self.assertEqual(client.client.secret, self.config["CLOUDSTACK_SECRET_KEY"])

    def test_init_no_api_url(self):
        with self.assertRaises(config.MissConfigurationError) as cm:
            cloudstack.CloudStackManager()
        exc = cm.exception
        self.assertEqual(("env var CLOUDSTACK_API_URL is required",),
                         exc.args)

    def test_init_no_api_key(self):
        with self.assertRaises(config.MissConfigurationError) as cm:
            cloudstack.CloudStackManager({"CLOUDSTACK_API_URL": "something"})
        exc = cm.exception
        self.assertEqual(("env var CLOUDSTACK_API_KEY is required",),
                         exc.args)

    def test_init_no_secret_key(self):
        with self.assertRaises(config.MissConfigurationError) as cm:
            cloudstack.CloudStackManager({
                "CLOUDSTACK_API_URL": "something",
                "CLOUDSTACK_API_KEY": "not_secret",
            })
        exc = cm.exception
        self.assertEqual(("env var CLOUDSTACK_SECRET_KEY is required",),
                         exc.args)

    def test_create(self):
        self.config.update({
            "CLOUDSTACK_TEMPLATE_ID": "abc123",
            "CLOUDSTACK_SERVICE_OFFERING_ID": "qwe123",
            "CLOUDSTACK_ZONE_ID": "zone1",
            "CLOUDSTACK_PROJECT_ID": "project-123",
            "CLOUDSTACK_NETWORK_IDS": "net-123",
            "CLOUDSTACK_GROUP": "feaas",
        })

        client_mock = mock.Mock()
        client_mock.deployVirtualMachine.return_value = {"id": "abc123",
                                                         "jobid": "qwe321"}
        vm = {"id": "abc123", "nic": [{"ipaddress": "10.0.0.1"}]}
        client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}

        manager = cloudstack.CloudStackManager(self.config)
        manager.client = client_mock
        host = manager.create_host('xxx')
        self.assertEqual("abc123", host.id)
        self.assertEqual("10.0.0.1", host.dns_name)
        create_data = {
            "group": "feaas",
            "displayname": "feaas_xxx",
            "templateid": "abc123",
            "zoneid": "zone1",
            "serviceofferingid": "qwe123",
            "networkids": "net-123",
            "projectid": "project-123",
        }
        client_mock.deployVirtualMachine.assert_called_with(create_data)
        client_mock.wait_for_job.assert_called_with('qwe321', 100)

    def test_create_with_tags(self):
        self.config.update({
            "CLOUDSTACK_TEMPLATE_ID": "abc123",
            "CLOUDSTACK_SERVICE_OFFERING_ID": "qwe123",
            "CLOUDSTACK_ZONE_ID": "zone1",
            "CLOUDSTACK_PROJECT_ID": "project-123",
            "CLOUDSTACK_NETWORK_IDS": "net-123",
            "CLOUDSTACK_GROUP": "feaas",
            "HOST_TAGS": "Name:something,monitor:1,wait=wat",
        })

        client_mock = mock.Mock()
        client_mock.deployVirtualMachine.return_value = {"id": "abc123",
                                                         "jobid": "qwe321"}
        vm = {"id": "abc123", "nic": [{"ipaddress": "10.0.0.1"}]}
        client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}

        manager = cloudstack.CloudStackManager(self.config)
        manager.client = client_mock
        host = manager.create_host('xxx')
        self.assertEqual("abc123", host.id)
        self.assertEqual("10.0.0.1", host.dns_name)
        create_data = {
            "group": "feaas",
            "displayname": "feaas_xxx",
            "templateid": "abc123",
            "zoneid": "zone1",
            "serviceofferingid": "qwe123",
            "networkids": "net-123",
            "projectid": "project-123",
        }
        client_mock.deployVirtualMachine.assert_called_with(create_data)
        client_mock.wait_for_job.assert_called_with('qwe321', 100)
        tag_data = {
            "resourcetype": "UserVm",
            "resourceids": "abc123",
            "projectid": "project-123",
            "tags[1].key": "Name",
            "tags[1].value": "something",
            "tags[2].key": "monitor",
            "tags[2].value": "1",
        }
        client_mock.createTags.assert_called_with(tag_data)

    def test_create_no_group(self):
        self.config.update({
            "CLOUDSTACK_TEMPLATE_ID": "abc123",
            "CLOUDSTACK_SERVICE_OFFERING_ID": "qwe123",
            "CLOUDSTACK_ZONE_ID": "zone1",
            "CLOUDSTACK_PROJECT_ID": "project-123",
            "CLOUDSTACK_NETWORK_IDS": "net-123",
        })

        client_mock = mock.Mock()
        client_mock.deployVirtualMachine.return_value = {"id": "abc123",
                                                         "jobid": "qwe321"}
        vm = {"id": "abc123", "nic": [{"ipaddress": "10.0.0.1"}]}
        client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}

        manager = cloudstack.CloudStackManager(self.config)
        manager.client = client_mock
        host = manager.create_host('xxx')
        self.assertEqual("abc123", host.id)
        self.assertEqual("10.0.0.1", host.dns_name)
        create_data = {
            "group": "",
            "displayname": "xxx",
            "templateid": "abc123",
            "zoneid": "zone1",
            "serviceofferingid": "qwe123",
            "networkids": "net-123",
            "projectid": "project-123",
        }
        client_mock.deployVirtualMachine.assert_called_with(create_data)
        client_mock.wait_for_job.assert_called_with('qwe321', 100)

    def test_create_no_project_id(self):
        self.config.update({
            "CLOUDSTACK_TEMPLATE_ID": "abc123",
            "CLOUDSTACK_SERVICE_OFFERING_ID": "qwe123",
            "CLOUDSTACK_ZONE_ID": "zone1",
            "CLOUDSTACK_NETWORK_IDS": "net-123",
            "CLOUDSTACK_GROUP": "feaas",
        })

        client_mock = mock.Mock()
        client_mock.deployVirtualMachine.return_value = {"id": "abc123",
                                                         "jobid": "qwe321"}
        vm = {"id": "abc123", "nic": [{"ipaddress": "10.0.0.1"}]}
        client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}

        manager = cloudstack.CloudStackManager(self.config)
        manager.client = client_mock
        host = manager.create_host()
        self.assertEqual("abc123", host.id)
        self.assertEqual("10.0.0.1", host.dns_name)
        create_data = {
            "group": "feaas",
            "displayname": "feaas",
            "templateid": "abc123",
            "zoneid": "zone1",
            "serviceofferingid": "qwe123",
            "networkids": "net-123",
        }
        client_mock.deployVirtualMachine.assert_called_with(create_data)
        client_mock.wait_for_job.assert_called_with('qwe321', 100)

    def test_create_no_network_id(self):
        self.config.update({
            "CLOUDSTACK_TEMPLATE_ID": "abc123",
            "CLOUDSTACK_SERVICE_OFFERING_ID": "qwe123",
            "CLOUDSTACK_ZONE_ID": "zone1",
            "CLOUDSTACK_GROUP": "feaas",
        })

        client_mock = mock.Mock()
        client_mock.deployVirtualMachine.return_value = {"id": "abc123",
                                                         "jobid": "qwe321"}
        vm = {"id": "abc123", "nic": [{"ipaddress": "10.0.0.1"}]}
        client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}

        manager = cloudstack.CloudStackManager(self.config)
        manager.client = client_mock
        host = manager.create_host()
        self.assertEqual("abc123", host.id)
        self.assertEqual("10.0.0.1", host.dns_name)
        create_data = {
            "group": "feaas",
            "displayname": "feaas",
            "templateid": "abc123",
            "zoneid": "zone1",
            "serviceofferingid": "qwe123",
        }
        client_mock.deployVirtualMachine.assert_called_with(create_data)
        client_mock.wait_for_job.assert_called_with('qwe321', 100)

    def test_create_invalid_response(self):
        self.config.update({
            "CLOUDSTACK_TEMPLATE_ID": "abc123",
            "CLOUDSTACK_SERVICE_OFFERING_ID": "qwe123",
            "CLOUDSTACK_ZONE_ID": "zone1",
            "CLOUDSTACK_GROUP": "feaas",
        })

        client_mock = mock.Mock()
        client_mock.deployVirtualMachine.return_value = {"error": "xxx"}
        vm = {"id": "abc123", "nic": [{"ipaddress": "10.0.0.1"}]}
        client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}

        manager = cloudstack.CloudStackManager(self.config)
        manager.client = client_mock
        with self.assertRaises(cloudstack.CloudStackException) as ctx:
            manager.create_host()
        exc = ctx.exception
        self.assertRegexpMatches(
            str(exc), r"unexpected response from deployVirtualMachine\({.+}\)"
            ", expected jobid key, got: {'error': 'xxx'}")
        create_data = {
            "group": "feaas",
            "displayname": "feaas",
            "templateid": "abc123",
            "zoneid": "zone1",
            "serviceofferingid": "qwe123",
        }
        client_mock.deployVirtualMachine.assert_called_with(create_data)

    def test_create_public_network_index(self):
        self.config.update({
            "CLOUDSTACK_TEMPLATE_ID": "abc123",
            "CLOUDSTACK_SERVICE_OFFERING_ID": "qwe123",
            "CLOUDSTACK_ZONE_ID": "zone1",
            "CLOUDSTACK_GROUP": "feaas",
            "CLOUDSTACK_PUBLIC_NETWORK_INDEX": "1",
        })

        client_mock = mock.Mock()
        client_mock.deployVirtualMachine.return_value = {"id": "abc123",
                                                         "jobid": "qwe321"}
        vm = {"id": "abc123", "nic": [{"ipaddress": "10.0.0.1"},
                                      {"ipaddress": "192.168.1.1"},
                                      {"ipaddress": "172.16.42.1"}]}
        client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}

        manager = cloudstack.CloudStackManager(self.config)
        manager.client = client_mock
        host = manager.create_host()
        self.assertEqual("abc123", host.id)
        self.assertEqual("192.168.1.1", host.dns_name)
        create_data = {
            "group": "feaas",
            "displayname": "feaas",
            "templateid": "abc123",
            "zoneid": "zone1",
            "serviceofferingid": "qwe123",
        }
        client_mock.deployVirtualMachine.assert_called_with(create_data)
        client_mock.wait_for_job.assert_called_with('qwe321', 100)

    def test_create_public_multi_nic_no_network_index(self):
        self.config.update({
            "CLOUDSTACK_TEMPLATE_ID": "abc123",
            "CLOUDSTACK_SERVICE_OFFERING_ID": "qwe123",
            "CLOUDSTACK_ZONE_ID": "zone1",
            "CLOUDSTACK_GROUP": "feaas",
        })

        client_mock = mock.Mock()
        client_mock.deployVirtualMachine.return_value = {"id": "abc123",
                                                         "jobid": "qwe321"}
        vm = {"id": "abc123", "nic": [{"ipaddress": "10.0.0.1"},
                                      {"ipaddress": "192.168.1.1"},
                                      {"ipaddress": "172.16.42.1"}]}
        client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}

        manager = cloudstack.CloudStackManager(self.config)
        manager.client = client_mock
        host = manager.create_host()
        self.assertEqual("abc123", host.id)
        self.assertEqual("10.0.0.1", host.dns_name)
        create_data = {
            "group": "feaas",
            "displayname": "feaas",
            "templateid": "abc123",
            "zoneid": "zone1",
            "serviceofferingid": "qwe123",
        }
        client_mock.deployVirtualMachine.assert_called_with(create_data)
        client_mock.wait_for_job.assert_called_with('qwe321', 100)

    def test_create_timeout(self):
        self.config.update({
            "CLOUDSTACK_TEMPLATE_ID": "abc123",
            "CLOUDSTACK_SERVICE_OFFERING_ID": "qwe123",
            "CLOUDSTACK_ZONE_ID": "zone1",
            "CLOUDSTACK_GROUP": "feaas",
            "CLOUDSTACK_MAX_TRIES": 1,
        })

        client_mock = mock.Mock()
        client_mock.deployVirtualMachine.return_value = {"id": "abc123",
                                                         "jobid": "qwe321"}
        vm = {"id": "abc123", "nic": [{"ipaddress": "10.0.0.1"}]}
        client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}
        client_mock.wait_for_job.side_effect = cloudstack_client.MaxTryWaitingForJobError(1, 'qwe321')

        manager = cloudstack.CloudStackManager(self.config)
        manager.client = client_mock
        with self.assertRaises(cloudstack_client.MaxTryWaitingForJobError) as cm:
            manager.create_host()
        exc = cm.exception
        self.assertEqual(1, exc.max_tries)
        self.assertEqual("qwe321", exc.job_id)
        self.assertEqual("exceeded 1 tries waiting for job qwe321", str(exc))
        create_data = {
            "group": "feaas",
            "displayname": "feaas",
            "templateid": "abc123",
            "zoneid": "zone1",
            "serviceofferingid": "qwe123",
        }
        client_mock.wait_for_job.assert_called_with('qwe321', 1)
        client_mock.deployVirtualMachine.assert_called_with(create_data)

    def test_create_alternatives(self):
        self.config.update({
            "CLOUDSTACK_GROUP": "feaas",
            "CLOUDSTACK_TEMPLATE_ID": "template-base",
            "CLOUDSTACK_PROJECT_ID": "project-base",

            "CLOUDSTACK_ZONE_ID_0": "zone0",
            "CLOUDSTACK_NETWORK_IDS_0": "net0",
            "CLOUDSTACK_SERVICE_OFFERING_ID_0": "offering0",

            "CLOUDSTACK_ZONE_ID_1": "zone1",
            "CLOUDSTACK_NETWORK_IDS_1": "net1",
            "CLOUDSTACK_SERVICE_OFFERING_ID_1": "offering1",
            "CLOUDSTACK_PROJECT_ID_1": "project1",
        })

        client_mock = mock.Mock()
        client_mock.deployVirtualMachine.return_value = {"id": "abc123",
                                                         "jobid": "qwe321"}
        vm = {"id": "abc123", "nic": [{"ipaddress": "10.0.0.1"}]}
        client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}

        manager = cloudstack.CloudStackManager(self.config)
        manager.client = client_mock
        host = manager.create_host('xxx', alternative_id=0)
        self.assertEqual("abc123", host.id)
        self.assertEqual("10.0.0.1", host.dns_name)
        create_data = {
            "group": "feaas",
            "displayname": "feaas_xxx",
            "templateid": "template-base",
            "zoneid": "zone0",
            "serviceofferingid": "offering0",
            "networkids": "net0",
            "projectid": "project-base",
        }
        client_mock.deployVirtualMachine.assert_called_with(create_data)
        client_mock.wait_for_job.assert_called_with('qwe321', 100)

        host = manager.create_host('xxx', alternative_id=1)
        create_data = {
            "group": "feaas",
            "displayname": "feaas_xxx",
            "templateid": "template-base",
            "zoneid": "zone1",
            "serviceofferingid": "offering1",
            "networkids": "net1",
            "projectid": "project1",
        }
        client_mock.deployVirtualMachine.assert_called_with(create_data)

    def test_destroy_host(self):
        manager = cloudstack.CloudStackManager(self.config)
        manager.client = mock.Mock()
        manager.destroy_host('host-id')
        manager.client.destroyVirtualMachine.assert_called_with({'id': 'host-id'})

    def test_restore_host(self):
        manager = cloudstack.CloudStackManager(self.config)
        manager.client = mock.Mock()
        manager.restore_host('host-id')
        manager.client.make_request.assert_called_with('restoreVirtualMachine',
                                                       {'virtualmachineid': 'host-id'},
                                                       response_key='restorevmresponse')

    def test_stop_host(self):
        manager = cloudstack.CloudStackManager(self.config)
        manager.client = mock.Mock()
        manager.stop_host('host-id', True)
        manager.client.stopVirtualMachine.assert_called_with({'id': 'host-id', 'forced': True})

    def test_start_host(self):
        manager = cloudstack.CloudStackManager(self.config)
        manager.client = mock.Mock()
        manager.start_host('host-id')
        manager.client.startVirtualMachine.assert_called_with({'id': 'host-id'})
