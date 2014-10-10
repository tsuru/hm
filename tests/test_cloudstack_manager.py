# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import unittest

import mock

from hm import config
from hm.managers import cloudstack


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
        client_mock.queryAsyncJobResult.return_value = {"jobstatus": 1}
        vm = {"id": "abc123", "nic": [{"ipaddress": "10.0.0.1"}]}
        client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}

        manager = cloudstack.CloudStackManager(self.config)
        manager.client = client_mock
        host = manager.create()
        self.assertEqual("abc123", host.id)
        self.assertEqual("10.0.0.1", host.dns_name)
        create_data = {
            "group": "feaas",
            "templateid": "abc123",
            "zoneid": "zone1",
            "serviceofferingid": "qwe123",
            "networkids": "net-123",
            "projectid": "project-123",
        }
        client_mock.deployVirtualMachine.assert_called_with(create_data)

#     @mock.patch("uuid.uuid4")
#     def test_start_instance_no_project_id(self, uuid):
#         self.set_api_envs()
#         self.addCleanup(self.del_api_envs)
#         self.set_vm_envs(network_ids="net-123")
#         self.addCleanup(self.del_vm_envs)
#         uuid.return_value = "uuid_val"
#         instance = storage.Instance(name="some_instance", units=[])
#         strg_mock = mock.Mock()
#         strg_mock.retrieve_instance.return_value = instance
#         client_mock = mock.Mock()
#         client_mock.deployVirtualMachine.return_value = {"id": "abc123",
#                                                          "jobid": "qwe321"}
#         client_mock.queryAsyncJobResult.return_value = {"jobstatus": 1}
#         vm = {"id": "abc123", "nic": [{"ipaddress": "10.0.0.1"}]}
#         client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}
#         client_mock.encode_user_data.return_value = user_data = mock.Mock()
#         manager = cloudstack.CloudStackManager(storage=strg_mock)
#         manager.client = client_mock
#         got_instance = manager.start_instance("some_instance")
#         self.assertEqual(instance, got_instance)
#         self.assertEqual(1, len(instance.units))
#         unit = instance.units[0]
#         self.assertEqual("abc123", unit.id)
#         self.assertEqual("uuid_val", unit.secret)
#         self.assertEqual(instance, unit.instance)
#         self.assertEqual("10.0.0.1", unit.dns_name)
#         self.assertEqual("creating", unit.state)
#         strg_mock.retrieve_instance.assert_called_with(name="some_instance")
#         create_data = {"group": "feaas", "templateid": self.template_id,
#                        "zoneid": self.zone_id,
#                        "serviceofferingid": self.service_offering_id,
#                        "userdata": user_data, "networkids": self.network_ids}
#         client_mock.deployVirtualMachine.assert_called_with(create_data)
#         actual_user_data = manager.get_user_data("uuid_val")
#         client_mock.encode_user_data.assert_called_with(actual_user_data)

#     @mock.patch("uuid.uuid4")
#     def test_start_instance_no_network_id(self, uuid):
#         self.set_api_envs()
#         self.addCleanup(self.del_api_envs)
#         self.set_vm_envs(project_id="proj-123")
#         self.addCleanup(self.del_vm_envs)
#         uuid.return_value = "uuid_val"
#         instance = storage.Instance(name="some_instance", units=[])
#         strg_mock = mock.Mock()
#         strg_mock.retrieve_instance.return_value = instance
#         client_mock = mock.Mock()
#         client_mock.deployVirtualMachine.return_value = {"id": "abc123",
#                                                          "jobid": "qwe321"}
#         client_mock.queryAsyncJobResult.return_value = {"jobstatus": 1}
#         vm = {"id": "abc123", "nic": []}
#         client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}
#         client_mock.encode_user_data.return_value = user_data = mock.Mock()
#         manager = cloudstack.CloudStackManager(storage=strg_mock)
#         manager.client = client_mock
#         got_instance = manager.start_instance("some_instance")
#         self.assertEqual(instance, got_instance)
#         self.assertEqual(1, len(instance.units))
#         unit = instance.units[0]
#         self.assertEqual("abc123", unit.id)
#         self.assertEqual("uuid_val", unit.secret)
#         self.assertEqual(instance, unit.instance)
#         self.assertEqual("", unit.dns_name)
#         self.assertEqual("creating", unit.state)
#         strg_mock.retrieve_instance.assert_called_with(name="some_instance")
#         create_data = {"group": "feaas", "templateid": self.template_id,
#                        "zoneid": self.zone_id,
#                        "serviceofferingid": self.service_offering_id,
#                        "userdata": user_data, "projectid": self.project_id}
#         client_mock.deployVirtualMachine.assert_called_with(create_data)
#         actual_user_data = manager.get_user_data("uuid_val")
#         client_mock.encode_user_data.assert_called_with(actual_user_data)

#     @mock.patch("uuid.uuid4")
#     def test_start_instance_public_network_name(self, uuid):
#         def cleanup():
#             del os.environ["CLOUDSTACK_PUBLIC_NETWORK_NAME"]
#         self.addCleanup(cleanup)
#         os.environ["CLOUDSTACK_PUBLIC_NETWORK_NAME"] = "NOPOWER"
#         self.set_api_envs()
#         self.addCleanup(self.del_api_envs)
#         self.set_vm_envs(project_id="project-123", network_ids="net-123")
#         self.addCleanup(self.del_vm_envs)
#         uuid.return_value = "uuid_val"
#         instance = storage.Instance(name="some_instance", units=[])
#         strg_mock = mock.Mock()
#         strg_mock.retrieve_instance.return_value = instance
#         client_mock = mock.Mock()
#         client_mock.deployVirtualMachine.return_value = {"id": "abc123",
#                                                          "jobid": "qwe321"}
#         client_mock.queryAsyncJobResult.return_value = {"jobstatus": 1}
#         vm = {"id": "abc123", "nic": [{"ipaddress": "10.0.0.1", "networkname": "POWERNET"},
#                                       {"ipaddress": "192.168.1.1", "networkname": "NOPOWER"},
#                                       {"ipaddress": "172.16.42.1", "networkname": "KPOWER"}]}
#         client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}
#         client_mock.encode_user_data.return_value = user_data = mock.Mock()
#         manager = cloudstack.CloudStackManager(storage=strg_mock)
#         manager.client = client_mock
#         got_instance = manager.start_instance("some_instance")
#         self.assertEqual(instance, got_instance)
#         self.assertEqual(1, len(instance.units))
#         unit = instance.units[0]
#         self.assertEqual("abc123", unit.id)
#         self.assertEqual("uuid_val", unit.secret)
#         self.assertEqual(instance, unit.instance)
#         self.assertEqual("192.168.1.1", unit.dns_name)
#         self.assertEqual("creating", unit.state)
#         strg_mock.retrieve_instance.assert_called_with(name="some_instance")
#         create_data = {"group": "feaas", "templateid": self.template_id,
#                        "zoneid": self.zone_id,
#                        "serviceofferingid": self.service_offering_id,
#                        "userdata": user_data, "networkids": self.network_ids,
#                        "projectid": self.project_id}
#         client_mock.deployVirtualMachine.assert_called_with(create_data)
#         actual_user_data = manager.get_user_data("uuid_val")
#         client_mock.encode_user_data.assert_called_with(actual_user_data)

#     @mock.patch("uuid.uuid4")
#     def test_start_instance_multi_nic_no_network_name(self, uuid):
#         self.set_api_envs()
#         self.addCleanup(self.del_api_envs)
#         self.set_vm_envs(project_id="project-123", network_ids="net-123")
#         self.addCleanup(self.del_vm_envs)
#         uuid.return_value = "uuid_val"
#         instance = storage.Instance(name="some_instance", units=[])
#         strg_mock = mock.Mock()
#         strg_mock.retrieve_instance.return_value = instance
#         client_mock = mock.Mock()
#         client_mock.deployVirtualMachine.return_value = {"id": "abc123",
#                                                          "jobid": "qwe321"}
#         client_mock.queryAsyncJobResult.return_value = {"jobstatus": 1}
#         vm = {"id": "abc123", "nic": [{"ipaddress": "10.0.0.1", "networkname": "POWERNET"},
#                                       {"ipaddress": "192.168.1.1", "networkname": "NOPOWER"},
#                                       {"ipaddress": "172.16.42.1", "networkname": "KPOWER"}]}
#         client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}
#         client_mock.encode_user_data.return_value = user_data = mock.Mock()
#         manager = cloudstack.CloudStackManager(storage=strg_mock)
#         manager.client = client_mock
#         got_instance = manager.start_instance("some_instance")
#         self.assertEqual(instance, got_instance)
#         self.assertEqual(1, len(instance.units))
#         unit = instance.units[0]
#         self.assertEqual("abc123", unit.id)
#         self.assertEqual("uuid_val", unit.secret)
#         self.assertEqual(instance, unit.instance)
#         self.assertEqual("172.16.42.1", unit.dns_name)
#         self.assertEqual("creating", unit.state)
#         strg_mock.retrieve_instance.assert_called_with(name="some_instance")
#         create_data = {"group": "feaas", "templateid": self.template_id,
#                        "zoneid": self.zone_id,
#                        "serviceofferingid": self.service_offering_id,
#                        "userdata": user_data, "networkids": self.network_ids,
#                        "projectid": self.project_id}
#         client_mock.deployVirtualMachine.assert_called_with(create_data)
#         actual_user_data = manager.get_user_data("uuid_val")
#         client_mock.encode_user_data.assert_called_with(actual_user_data)

#     def test_start_instance_timeout(self):
#         def cleanup():
#             del os.environ["CLOUDSTACK_MAX_TRIES"]
#         self.addCleanup(cleanup)
#         os.environ["CLOUDSTACK_MAX_TRIES"] = "1"
#         self.set_api_envs()
#         self.addCleanup(self.del_api_envs)
#         self.set_vm_envs()
#         self.addCleanup(self.del_vm_envs)
#         instance = storage.Instance(name="some_instance", units=[])
#         strg_mock = mock.Mock()
#         strg_mock.retrieve_instance.return_value = instance
#         client_mock = mock.Mock()
#         client_mock.deployVirtualMachine.return_value = {"id": "abc123",
#                                                          "jobid": "qwe321"}
#         client_mock.queryAsyncJobResult.return_value = {"jobstatus": 0}
#         manager = cloudstack.CloudStackManager(storage=strg_mock)
#         manager.client = client_mock
#         with self.assertRaises(cloudstack.MaxTryExceededError) as cm:
#             manager.start_instance("some_instance")
#         exc = cm.exception
#         self.assertEqual(1, exc.max_tries)

#     def test_terminate_instance(self):
#         self.set_api_envs()
#         self.addCleanup(self.del_api_envs)
#         instance = storage.Instance(name="some_instance",
#                                     units=[storage.Unit(id="vm-123"),
#                                            storage.Unit(id="vm-456")])
#         strg_mock = mock.Mock()
#         strg_mock.retrieve_instance.return_value = instance
#         manager = cloudstack.CloudStackManager(storage=strg_mock)
#         manager.client = client_mock = mock.Mock()
#         got_instance = manager.terminate_instance("some_instance")
#         self.assertEqual(instance, got_instance)
#         expected_calls = [mock.call({"id": "vm-123"}), mock.call({"id": "vm-456"})]
#         self.assertEqual(expected_calls, client_mock.destroyVirtualMachine.call_args_list)

#     @mock.patch("sys.stderr")
#     def test_terminate_instance_ignores_exceptions(self, stderr):
#         self.set_api_envs()
#         self.addCleanup(self.del_api_envs)
#         instance = storage.Instance(name="some_instance",
#                                     units=[storage.Unit(id="vm-123"),
#                                            storage.Unit(id="vm-456")])
#         strg_mock = mock.Mock()
#         strg_mock.retrieve_instance.return_value = instance
#         client_mock = mock.Mock()
#         client_mock.destroyVirtualMachine.side_effect = Exception("wat", "wot")
#         manager = cloudstack.CloudStackManager(storage=strg_mock)
#         manager.client = client_mock
#         got_instance = manager.terminate_instance("some_instance")
#         self.assertEqual(instance, got_instance)
#         stderr.write.assert_called_with("[ERROR] Failed to terminate CloudStack VM: wat wot")

#     @mock.patch("uuid.uuid4")
#     def test_physical_scale_up(self, uuid):
#         self.set_api_envs()
#         self.addCleanup(self.del_api_envs)
#         self.set_vm_envs(project_id="project-123", network_ids="net-123")
#         self.addCleanup(self.del_vm_envs)
#         uuid.return_value = "uuid_val"
#         instance = storage.Instance(name="some_instance",
#                                     units=[storage.Unit(id="123")])
#         strg_mock = mock.Mock()
#         client_mock = mock.Mock()
#         client_mock.deployVirtualMachine.return_value = {"id": "abc123",
#                                                          "jobid": "qwe321"}
#         client_mock.queryAsyncJobResult.return_value = {"jobstatus": 1}
#         vm = {"id": "qwe123", "nic": [{"ipaddress": "10.0.0.5"}]}
#         client_mock.listVirtualMachines.return_value = {"virtualmachine": [vm]}
#         client_mock.encode_user_data.return_value = user_data = mock.Mock()
#         manager = cloudstack.CloudStackManager(storage=strg_mock)
#         manager.client = client_mock
#         units = manager.physical_scale(instance, 2)
#         self.assertEqual(2, len(instance.units))
#         self.assertEqual(1, len(units))
#         unit = instance.units[1]
#         self.assertEqual("qwe123", unit.id)
#         self.assertEqual("uuid_val", unit.secret)
#         self.assertEqual(instance, unit.instance)
#         self.assertEqual("10.0.0.5", unit.dns_name)
#         self.assertEqual("creating", unit.state)
#         create_data = {"group": "feaas", "templateid": self.template_id,
#                        "zoneid": self.zone_id,
#                        "serviceofferingid": self.service_offering_id,
#                        "userdata": user_data, "networkids": self.network_ids,
#                        "projectid": self.project_id}
#         client_mock.deployVirtualMachine.assert_called_with(create_data)
#         actual_user_data = manager.get_user_data("uuid_val")
#         client_mock.encode_user_data.assert_called_with(actual_user_data)

#     def test_physical_scale_down(self):
#         self.set_api_envs()
#         self.addCleanup(self.del_api_envs)
#         units = [storage.Unit(id="vm-123"), storage.Unit(id="vm-456"),
#                  storage.Unit(id="vm-789")]
#         instance = storage.Instance(name="some_instance", units=copy.deepcopy(units))
#         strg_mock = mock.Mock()
#         manager = cloudstack.CloudStackManager(storage=strg_mock)
#         manager.client = client_mock = mock.Mock()
#         got_units = manager.physical_scale(instance, 1)
#         self.assertEqual(1, len(instance.units))
#         self.assertEqual(2, len(got_units))
#         self.assertEqual("vm-789", instance.units[0].id)
#         expected_calls = [mock.call({"id": "vm-123"}), mock.call({"id": "vm-456"})]
#         self.assertEqual(expected_calls, client_mock.destroyVirtualMachine.call_args_list)


# class MaxTryExceededErrorTestCase(unittest.TestCase):

#     def test_error_message(self):
#         exc = cloudstack.MaxTryExceededError(40)
#         self.assertEqual(40, exc.max_tries)
#         self.assertEqual(("exceeded 40 tries",), exc.args)
