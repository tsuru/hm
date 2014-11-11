# coding: utf-8
import unittest

import mock
from networkapiclient.exception import IpNaoExisteError

from hm.lb_managers import networkapi_cloudstack
from hm.model import load_balancer, host


class NetworkApiCloudstackLBTestCase(unittest.TestCase):

    def setUp(self):
        self.conf = {
            'CLOUDSTACK_API_URL': 'http://localhost',
            'CLOUDSTACK_API_KEY': 'key',
            'CLOUDSTACK_SECRET_KEY': 'secret',
            'CLOUDSTACK_PROJECT_ID': 'proj-123',
            'CLOUDSTACK_VIP_NETWORK_INDEX': '1',

            'NETWORKAPI_ENDPOINT': 'http://networkapi.host',
            'NETWORKAPI_USER': 'tsuru',
            'NETWORKAPI_PASSWORD': 'secret',
            'NETWORKAPI_CLIENTE_TXT': 'client',
            'NETWORKAPI_FINALIDADE_TXT': 'destination',
            'NETWORKAPI_AMBIENTE_P44_TXT': 'environment',

            'VIP_HEALTHCHECK': 'GET /',
            'VIP_HEALTHCHECK_EXPECT': '55',
            'VIP_METHOD_BAL': 'brincation_uite_me',
            'VIP_PERSISTENCE': 'wat',
            'VIP_CACHE': 'powerful cache',
            'VIP_MAXCONN': '1500',
            'VIP_BUSINESS_AREA': 'business-area',
            'VIP_SERVICE_NAME': 'service-name',
            'VIP_PORT_MAPPING': '80:8080',
        }

    def test_init(self):
        manager = networkapi_cloudstack.NetworkApiCloudstackLB(self.conf)
        self.assertEqual(manager.cs_client.api_url, 'http://localhost')
        self.assertEqual(manager.cs_client.api_key, 'key')
        self.assertEqual(manager.cs_client.secret, 'secret')
        self.assertEqual(manager.create_project_id, 'proj-123')
        self.assertEqual(manager.networkapi_endpoint, 'http://networkapi.host')
        self.assertEqual(manager.networkapi_user, 'tsuru')
        self.assertEqual(manager.networkapi_password, 'secret')
        self.assertEqual(manager.vip_network_index, 1)
        self.assertEqual(manager.vip_config.environment_p44, 'environment')
        self.assertEqual(manager.vip_config.client, 'client')
        self.assertEqual(manager.vip_config.finality, 'destination')
        self.assertEqual(manager.vip_config.healthcheck, 'GET /')
        self.assertEqual(manager.vip_config.healthcheck_expect, '55')
        self.assertEqual(manager.vip_config.lb_method, 'brincation_uite_me')
        self.assertEqual(manager.vip_config.cache, 'powerful cache')
        self.assertEqual(manager.vip_config.maxconn, '1500')
        self.assertEqual(manager.vip_config.business_area, 'business-area')
        self.assertEqual(manager.vip_config.service_name, 'service-name')
        self.assertEqual(manager.vip_config.port_mapping, ["80:8080"])

    def test_init_multiple_ports(self):
        self.conf.update({
            'VIP_PORT_MAPPING': '80:8080,443:8081'
        })
        manager = networkapi_cloudstack.NetworkApiCloudstackLB(self.conf)
        self.assertEqual(manager.vip_config.port_mapping, ["80:8080", "443:8081"])

    @mock.patch("hm.lb_managers.networkapi_cloudstack.log")
    @mock.patch("networkapiclient.EnvironmentVIP.EnvironmentVIP")
    @mock.patch("networkapiclient.Ip.Ip")
    @mock.patch("networkapiclient.Vip.Vip")
    def test_create_load_balancer(self, Vip, Ip, EnvironmentVIP, logger):
        client_evip = mock.Mock()
        client_evip.search.return_value = {"environment_vip": {"id": 500}}
        EnvironmentVIP.return_value = client_evip
        client_ip = mock.Mock()
        client_ip.get_available_ip4_for_vip.return_value = {"ip": {"id": 303, "oct4": "7",
                                                                   "oct2": "168", "oct3": "1",
                                                                   "oct1": "192"}}
        Ip.return_value = client_ip
        client_vip = mock.Mock()
        client_vip.add.return_value = {"requisicao_vip": {"id": 27}}
        Vip.return_value = client_vip

        manager = networkapi_cloudstack.NetworkApiCloudstackLB(self.conf)
        lb = manager.create_load_balancer("tsuru")
        self.assertEqual(27, lb.id)
        self.assertEqual(303, lb.ip_id)
        self.assertEqual("192.168.1.7", lb.address)
        self.assertEqual("tsuru", lb.name)
        self.assertEqual("proj-123", lb.project_id)

        EnvironmentVIP.assert_called_with(self.conf["NETWORKAPI_ENDPOINT"], self.conf["NETWORKAPI_USER"],
                                          self.conf["NETWORKAPI_PASSWORD"])
        Ip.assert_called_with(self.conf["NETWORKAPI_ENDPOINT"], self.conf["NETWORKAPI_USER"],
                              self.conf["NETWORKAPI_PASSWORD"])
        Vip.assert_called_with(self.conf["NETWORKAPI_ENDPOINT"], self.conf["NETWORKAPI_USER"],
                               self.conf["NETWORKAPI_PASSWORD"])
        client_evip.search.assert_called_with(ambiente_p44_txt=self.conf["NETWORKAPI_AMBIENTE_P44_TXT"],
                                              cliente_txt=self.conf["NETWORKAPI_CLIENTE_TXT"],
                                              finalidade_txt=self.conf["NETWORKAPI_FINALIDADE_TXT"])
        client_ip.get_available_ip4_for_vip.assert_called_with(500, u"tsuru hm tsuru")
        client_vip.add.assert_called_with(id_ipv4=303, id_ipv6=None,
                                          id_healthcheck_expect=self.conf["VIP_HEALTHCHECK_EXPECT"],
                                          finality=self.conf["NETWORKAPI_FINALIDADE_TXT"],
                                          client=self.conf["NETWORKAPI_CLIENTE_TXT"],
                                          environment=self.conf["NETWORKAPI_AMBIENTE_P44_TXT"],
                                          cache=self.conf["VIP_CACHE"],
                                          method_bal=self.conf["VIP_METHOD_BAL"],
                                          persistence=self.conf["VIP_PERSISTENCE"],
                                          healthcheck_type=u"HTTP",
                                          timeout=u"5",
                                          healthcheck=self.conf["VIP_HEALTHCHECK"],
                                          host="tsuru.hm.tsuru",
                                          maxcon=self.conf["VIP_MAXCONN"],
                                          areanegocio=self.conf["VIP_BUSINESS_AREA"],
                                          nome_servico=self.conf["VIP_SERVICE_NAME"],
                                          reals=[], reals_prioritys=[],
                                          reals_weights=[], ports=["80:8080"], l7_filter=None)
        client_vip.validate.assert_called_with(27)
        client_vip.criar.assert_called_with(27)
        logger.debug.assert_called_with(u"VIP request 27 successfully created.")

    @mock.patch("hm.lb_managers.networkapi_cloudstack.CloudStack")
    @mock.patch("networkapiclient.EnvironmentVIP.EnvironmentVIP")
    @mock.patch("networkapiclient.Ip.Ip")
    @mock.patch("networkapiclient.Vip.Vip")
    def test_create_vip_failure(self, Vip, Ip, EnvironmentVIP, CloudStack):
        client_evip = mock.Mock()
        client_evip.search.return_value = {"environment_vip": {"id": 500}}
        EnvironmentVIP.return_value = client_evip
        client_ip = mock.Mock()
        client_ip.get_available_ip4_for_vip.return_value = {"ip": {"id": 303}}
        Ip.return_value = client_ip
        client_vip = mock.Mock()
        client_vip.add.side_effect = Exception("Cannot create vip")
        Vip.return_value = client_vip
        manager = networkapi_cloudstack.NetworkApiCloudstackLB(self.conf)
        with self.assertRaises(Exception) as cm:
            manager.create_load_balancer("tsuru")
        exc = cm.exception
        self.assertEqual(("Cannot create vip",), exc.args)
        client_evip.search.assert_called_with(ambiente_p44_txt=self.conf["NETWORKAPI_AMBIENTE_P44_TXT"],
                                              cliente_txt=self.conf["NETWORKAPI_CLIENTE_TXT"],
                                              finalidade_txt=self.conf["NETWORKAPI_FINALIDADE_TXT"])
        client_ip.get_available_ip4_for_vip.assert_called_with(500, u"tsuru hm tsuru")
        client_ip.delete_ip4.assert_called_with(303)

    @mock.patch("hm.lb_managers.networkapi_cloudstack.CloudStack")
    @mock.patch("networkapiclient.EnvironmentVIP.EnvironmentVIP")
    @mock.patch("networkapiclient.Ip.Ip")
    @mock.patch("networkapiclient.Vip.Vip")
    def test_create_vip_failure_on_validate(self, Vip, Ip, EnvironmentVIP, CloudStack):
        client_evip = mock.Mock()
        client_evip.search.return_value = {"environment_vip": {"id": 500}}
        EnvironmentVIP.return_value = client_evip
        client_ip = mock.Mock()
        client_ip.get_available_ip4_for_vip.return_value = {"ip": {"id": 303}}
        Ip.return_value = client_ip
        client_vip = mock.Mock()
        client_vip.add.return_value = {"requisicao_vip": {"id": 27}}
        client_vip.validate.side_effect = Exception("Cannot validate vip")
        Vip.return_value = client_vip
        manager = networkapi_cloudstack.NetworkApiCloudstackLB(self.conf)
        with self.assertRaises(Exception) as cm:
            manager.create_load_balancer("tsuru")
        exc = cm.exception
        self.assertEqual(("Cannot validate vip",), exc.args)
        client_evip.search.assert_called_with(ambiente_p44_txt=self.conf["NETWORKAPI_AMBIENTE_P44_TXT"],
                                              cliente_txt=self.conf["NETWORKAPI_CLIENTE_TXT"],
                                              finalidade_txt=self.conf["NETWORKAPI_FINALIDADE_TXT"])
        client_ip.get_available_ip4_for_vip.assert_called_with(500, u"tsuru hm tsuru")
        client_ip.delete_ip4.assert_called_with(303)
        client_vip.remove_script.assert_called_with(27)
        client_vip.remover.assert_called_with(27)

    @mock.patch("hm.lb_managers.networkapi_cloudstack.log")
    @mock.patch("hm.lb_managers.networkapi_cloudstack.CloudStack")
    @mock.patch("networkapiclient.EnvironmentVIP.EnvironmentVIP")
    @mock.patch("networkapiclient.Ip.Ip")
    @mock.patch("networkapiclient.Vip.Vip")
    def test_create_vip_failure_on_remove(self, Vip, Ip, EnvironmentVIP, CloudStack, logger):
        client_evip = mock.Mock()
        client_evip.search.return_value = {"environment_vip": {"id": 500}}
        EnvironmentVIP.return_value = client_evip
        client_ip = mock.Mock()
        client_ip.get_available_ip4_for_vip.return_value = {"ip": {"id": 303}}
        Ip.return_value = client_ip
        client_vip = mock.Mock()
        client_vip.add.return_value = {"requisicao_vip": {"id": 27}}
        client_vip.validate.side_effect = Exception("Cannot validate vip")
        client_vip.remover.side_effect = Exception("Cannot remove vip")
        Vip.return_value = client_vip
        manager = networkapi_cloudstack.NetworkApiCloudstackLB(self.conf)
        with self.assertRaises(Exception) as cm:
            manager.create_load_balancer("tsuru")
        exc = cm.exception
        self.assertEqual(("Cannot validate vip",), exc.args)
        client_evip.search.assert_called_with(ambiente_p44_txt=self.conf["NETWORKAPI_AMBIENTE_P44_TXT"],
                                              cliente_txt=self.conf["NETWORKAPI_CLIENTE_TXT"],
                                              finalidade_txt=self.conf["NETWORKAPI_FINALIDADE_TXT"])
        client_ip.get_available_ip4_for_vip.assert_called_with(500, u"tsuru hm tsuru")
        client_ip.delete_ip4.assert_called_with(303)
        client_vip.remove_script.assert_called_with(27)
        client_vip.remover.assert_called_with(27)
        logger.error.assert_called_with("Failed to remove the VIP 27: Cannot remove vip")

    @mock.patch("hm.lb_managers.networkapi_cloudstack.CloudStack")
    @mock.patch("networkapiclient.Vip.Vip")
    @mock.patch("networkapiclient.Ip.Ip")
    def test_destroy_load_balancer(self, Ip, Vip, CloudStack):
        client_vip = mock.Mock()
        Vip.return_value = client_vip
        client_ip = mock.Mock()
        Ip.return_value = client_ip
        cloudstack_client = CloudStack.return_value

        lb = load_balancer.LoadBalancer(
            "404", "myapp", "192.168.1.1",
            ip_id="303",
            project_id="project_id-x"
        )
        manager = networkapi_cloudstack.NetworkApiCloudstackLB(self.conf)
        manager.destroy_load_balancer(lb)
        Vip.assert_called_with(self.conf["NETWORKAPI_ENDPOINT"], self.conf["NETWORKAPI_USER"],
                               self.conf["NETWORKAPI_PASSWORD"])
        client_vip.remove_script.assert_called_with("404")
        client_vip.remover.assert_called_with("404")
        Ip.assert_called_with(self.conf["NETWORKAPI_ENDPOINT"], self.conf["NETWORKAPI_USER"],
                              self.conf["NETWORKAPI_PASSWORD"])
        client_ip.delete_ip4.assert_called_with("303")
        data = {"projectid": "project_id-x", "vipid": "404"}
        cloudstack_client.removeGloboNetworkVip.assert_called_with(data)

    @mock.patch("hm.lb_managers.networkapi_cloudstack.CloudStack")
    @mock.patch("networkapiclient.Vip.Vip")
    @mock.patch("networkapiclient.Ip.Ip")
    def test_remove_vip_ip_not_found(self, Ip, Vip, CloudStack):
        client_vip = mock.Mock()
        Vip.return_value = client_vip
        client_ip = mock.Mock()
        client_ip.delete_ip4.side_effect = IpNaoExisteError("303")
        Ip.return_value = client_ip
        lb = load_balancer.LoadBalancer(
            "404", "myapp", "192.168.1.1",
            ip_id="303",
            project_id="project_id-x"
        )
        manager = networkapi_cloudstack.NetworkApiCloudstackLB(self.conf)
        manager.destroy_load_balancer(lb)
        Vip.assert_called_with(self.conf["NETWORKAPI_ENDPOINT"], self.conf["NETWORKAPI_USER"],
                               self.conf["NETWORKAPI_PASSWORD"])
        client_vip.remove_script.assert_called_with("404")
        client_vip.remover.assert_called_with("404")
        Ip.assert_called_with(self.conf["NETWORKAPI_ENDPOINT"], self.conf["NETWORKAPI_USER"],
                              self.conf["NETWORKAPI_PASSWORD"])
        client_ip.delete_ip4.assert_called_with("303")

    @mock.patch("hm.lb_managers.networkapi_cloudstack.CloudStack")
    def test_attach_real(self, CloudStack):
        self.conf.update({'CLOUDSTACK_VIP_NETWORK_INDEX': '0'})
        vms = {"virtualmachine": [{"id": "abc123", "nic": [{"id": "def456", "networkid": "netid1"}]}]}
        CloudStack.return_value = cloudstack_client = mock.Mock()
        cloudstack_client.listVirtualMachines.return_value = vms

        manager = networkapi_cloudstack.NetworkApiCloudstackLB(self.conf)
        lb = load_balancer.LoadBalancer(
            "500", "myapp", "192.168.1.1",
            ip_id="303",
            project_id=None,
        )
        h = host.Host('abc123', 'name.host')
        manager.attach_real(lb, h)
        list_data = {"id": "abc123"}
        cloudstack_client.listVirtualMachines.assert_called_with(list_data)
        net_data = {"networkid": "netid1", "vipid": "500"}
        cloudstack_client.addGloboNetworkVipToAccount.assert_called_with(net_data)
        assoc_data = {"nicid": "def456", "vipid": "500"}
        cloudstack_client.associateGloboNetworkRealToVip.assert_called_with(assoc_data)
        CloudStack.assert_called_with(
            self.conf["CLOUDSTACK_API_URL"],
            self.conf["CLOUDSTACK_API_KEY"],
            self.conf["CLOUDSTACK_SECRET_KEY"])

    @mock.patch("hm.lb_managers.networkapi_cloudstack.CloudStack")
    def test_attach_real_with_project_id(self, CloudStack):
        self.conf.update({'CLOUDSTACK_VIP_NETWORK_INDEX': '0'})
        vms = {"virtualmachine": [{"id": "abc123", "nic": [{"id": "def456", "networkid": "netid1"}]}]}
        CloudStack.return_value = cloudstack_client = mock.Mock()
        cloudstack_client.listVirtualMachines.return_value = vms

        manager = networkapi_cloudstack.NetworkApiCloudstackLB(self.conf)
        lb = load_balancer.LoadBalancer(
            "500", "myapp", "192.168.1.1",
            ip_id="303",
            project_id="project_id-x"
        )
        h = host.Host('abc123', 'name.host')
        manager.attach_real(lb, h)
        list_data = {"id": "abc123", "projectid": "project_id-x"}
        cloudstack_client.listVirtualMachines.assert_called_with(list_data)
        net_data = {"networkid": "netid1", "vipid": "500", "projectid": "project_id-x"}
        cloudstack_client.addGloboNetworkVipToAccount.assert_called_with(net_data)
        assoc_data = {"nicid": "def456", "vipid": "500", "projectid": "project_id-x"}
        cloudstack_client.associateGloboNetworkRealToVip.assert_called_with(assoc_data)
        CloudStack.assert_called_with(
            self.conf["CLOUDSTACK_API_URL"],
            self.conf["CLOUDSTACK_API_KEY"],
            self.conf["CLOUDSTACK_SECRET_KEY"])

    @mock.patch("hm.lb_managers.networkapi_cloudstack.CloudStack")
    def test_attach_real_with_network_index(self, CloudStack):
        vms = {"virtualmachine": [{"id": "abc123", "nic": [
            {"id": "def456", "networkid": "netid1"}, {"id": "second-id", "networkid": "netid2"}]}]}
        CloudStack.return_value = cloudstack_client = mock.Mock()
        cloudstack_client.listVirtualMachines.return_value = vms

        manager = networkapi_cloudstack.NetworkApiCloudstackLB(self.conf)
        lb = load_balancer.LoadBalancer(
            "500", "myapp", "192.168.1.1",
            ip_id="303",
            project_id=None,
        )
        h = host.Host('abc123', 'name.host')
        manager.attach_real(lb, h)
        list_data = {"id": "abc123"}
        cloudstack_client.listVirtualMachines.assert_called_with(list_data)
        net_data = {"networkid": "netid2", "vipid": "500"}
        cloudstack_client.addGloboNetworkVipToAccount.assert_called_with(net_data)
        assoc_data = {"nicid": "second-id", "vipid": "500"}
        cloudstack_client.associateGloboNetworkRealToVip.assert_called_with(assoc_data)
        CloudStack.assert_called_with(
            self.conf["CLOUDSTACK_API_URL"],
            self.conf["CLOUDSTACK_API_KEY"],
            self.conf["CLOUDSTACK_SECRET_KEY"])

    @mock.patch("hm.lb_managers.networkapi_cloudstack.CloudStack")
    def test_detach_real(self, CloudStack):
        self.conf.update({'CLOUDSTACK_VIP_NETWORK_INDEX': '0'})
        vms = {"virtualmachine": [{"id": "abc123", "nic": [{"id": "def456", "networkid": "netid1"}]}]}
        CloudStack.return_value = cloudstack_client = mock.Mock()
        cloudstack_client.listVirtualMachines.return_value = vms
        manager = networkapi_cloudstack.NetworkApiCloudstackLB(self.conf)
        lb = load_balancer.LoadBalancer(
            "500", "myapp", "192.168.1.1",
            ip_id="303",
            project_id=None
        )
        h = host.Host('abc123', 'name.host')
        manager.detach_real(lb, h)
        list_data = {"id": "abc123"}
        cloudstack_client.listVirtualMachines.assert_called_with(list_data)
        assoc_data = {"nicid": "def456", "vipid": "500"}
        cloudstack_client.disassociateGloboNetworkRealFromVip.assert_called_with(assoc_data)
        CloudStack.assert_called_with(
            self.conf["CLOUDSTACK_API_URL"],
            self.conf["CLOUDSTACK_API_KEY"],
            self.conf["CLOUDSTACK_SECRET_KEY"])

    @mock.patch("hm.lb_managers.networkapi_cloudstack.CloudStack")
    def test_detach_real_with_project_id(self, CloudStack):
        self.conf.update({'CLOUDSTACK_VIP_NETWORK_INDEX': '0'})
        vms = {"virtualmachine": [{"id": "abc123", "nic": [{"id": "def456", "networkid": "netid1"}]}]}
        CloudStack.return_value = cloudstack_client = mock.Mock()
        cloudstack_client.listVirtualMachines.return_value = vms
        manager = networkapi_cloudstack.NetworkApiCloudstackLB(self.conf)
        lb = load_balancer.LoadBalancer(
            "500", "myapp", "192.168.1.1",
            ip_id="303",
            project_id="pid-xxx"
        )
        h = host.Host('abc123', 'name.host')
        manager.detach_real(lb, h)
        list_data = {"id": "abc123", "projectid": "pid-xxx"}
        cloudstack_client.listVirtualMachines.assert_called_with(list_data)
        assoc_data = {"nicid": "def456", "vipid": "500", "projectid": "pid-xxx"}
        cloudstack_client.disassociateGloboNetworkRealFromVip.assert_called_with(assoc_data)
        CloudStack.assert_called_with(
            self.conf["CLOUDSTACK_API_URL"],
            self.conf["CLOUDSTACK_API_KEY"],
            self.conf["CLOUDSTACK_SECRET_KEY"])
