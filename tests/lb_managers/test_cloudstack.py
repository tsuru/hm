# coding: utf-8
import unittest

import mock

from hm.lb_managers import cloudstack
from hm.model import load_balancer, host


class CloudstackLBTestCase(unittest.TestCase):

    def setUp(self):
        self.conf = {
            'CLOUDSTACK_API_URL': 'http://localhost',
            'CLOUDSTACK_API_KEY': 'key',
            'CLOUDSTACK_SECRET_KEY': 'secret',
            'CLOUDSTACK_PROJECT_ID': 'proj-123',

            'CLOUDSTACK_LB_ASSOCIATE_IP_COMMAND': 'associateIpAddress',
            'CLOUDSTACK_LB_DISASSOCIATE_IP_COMMAND': 'disassociateIpAddress',
            'CLOUDSTACK_LB_ASSIGN_NETWORK_COMMAND': 'assignNetwork',
            'CLOUDSTACK_LB_NETWORK_ID': 'net-id',
            'CLOUDSTACK_LB_ZONE_ID': 'zone-id',
            'CLOUDSTACK_LB_VPC_ID': 'vpc-id',
            'CLOUDSTACK_LB_ENVIRONMENT_ID': 'env-id',
            'CLOUDSTACK_LB_ALGORITHM': 'leastconn',
            'CLOUDSTACK_LB_PORT_MAPPING': '80:8080,81:8081,82:8082',
            'CLOUDSTACK_LB_OPEN_FIREWALL': 'false',
            'CLOUDSTACK_LB_HEALTHCHECK': 'GET /',
            'CLOUDSTACK_LB_NETWORK_INDEX': '0',
            'CLOUDSTACK_LB_DOMAIN': 'abc.com',
            'CLOUDSTACK_LB_NETWORK_ID_0': 'net-id',
            'CLOUDSTACK_LB_NETWORK_ID_1': 'net-id2',
            'CLOUDSTACK_LB_NETWORK_ID_2': 'net-id3',
        }

    def test_init(self):
        manager = cloudstack.CloudstackLB(self.conf)
        self.assertEqual(manager.cs_client.api_url, 'http://localhost')
        self.assertEqual(manager.cs_client.api_key, 'key')
        self.assertEqual(manager.cs_client.secret, 'secret')
        self.assertEqual(manager.project_id, 'proj-123')
        self.assertEqual(manager.associate_ip_command, 'associateIpAddress')
        self.assertEqual(manager.disassociate_ip_command, 'disassociateIpAddress')
        self.assertEqual(manager.assign_network_command, 'assignNetwork')
        self.assertEqual(manager.lb_network_id, 'net-id')
        self.assertEqual(manager.lb_zone_id, 'zone-id')
        self.assertEqual(manager.lb_vpc_id, 'vpc-id')
        self.assertEqual(manager.lb_environment_id, 'env-id')
        self.assertEqual(manager.lb_algorithm, 'leastconn')
        self.assertEqual(manager.lb_port_mapping, '80:8080,81:8081,82:8082')
        self.assertEqual(manager.lb_open_firewall, 'false')
        self.assertEqual(manager.lb_healthcheck, 'GET /')
        self.assertEqual(manager.lb_network_index, 0)
        self.assertEqual(manager.lb_domain, 'abc.com')

    @mock.patch("hm.lb_managers.cloudstack.CloudStack")
    def test_create_load_balancer(self, cs_mock):
        cs_instance = cs_mock.return_value
        cs_instance.make_request.return_value = {'id': 'lb-ip-id', 'jobid': 'j1'}
        cs_instance.createLoadBalancerRule.return_value = {'id': 'lb-id', 'jobid': 'j2'}

        def wait_mock(jid, tries):
            if jid == 'j1':
                return {'jobresult': True}
            if jid == 'j2':
                return {'jobresult': {'loadbalancer': {'publicip': '192.168.1.5'}}}
        cs_instance.wait_for_job.side_effect = wait_mock
        manager = cloudstack.CloudstackLB(self.conf)
        lb = manager.create_load_balancer("tsuru")
        self.assertEqual('lb-id', lb.id)
        self.assertEqual('lb-ip-id', lb.ip_id)
        self.assertEqual("192.168.1.5", lb.address)
        self.assertEqual("tsuru", lb.name)
        self.assertEqual("proj-123", lb.project_id)
        cs_instance.make_request.assert_called_once_with('associateIpAddress', {
            'networkid': 'net-id',
            'projectid': 'proj-123',
            'zoneid': 'zone-id',
            'vpcid': 'vpc-id',
            'lbenvironmentid': 'env-id',
        }, response_key='associateipaddressresponse')
        cs_instance.createLoadBalancerRule.assert_called_once_with({
            'networkid': 'net-id',
            'algorithm': 'leastconn',
            'publicport': '80',
            'privateport': '8080',
            'openfirewall': 'false',
            'publicipid': 'lb-ip-id',
            'name': 'tsuru.abc.com',
            'additionalportmap': '81:8081,82:8082',
            'projectid': 'proj-123',
        })
        cs_instance.assignNetworksToLoadBalancerRule.assert_called_once_with({
            'id': 'lb-id',
            'projectid': 'proj-123',
            'networkids': 'net-id2,net-id3',
        })

    @mock.patch("hm.lb_managers.cloudstack.CloudStack")
    def test_create_load_balancer_rollback_ip(self, cs_mock):
        cs_instance = cs_mock.return_value
        cs_instance.make_request.return_value = {'id': 'lb-ip-id', 'jobid': 'j1'}

        def exc(*args):
            raise Exception("some error")
        cs_instance.createLoadBalancerRule.side_effect = exc
        cs_instance.wait_for_job.return_value = {'jobresult': True}
        manager = cloudstack.CloudstackLB(self.conf)
        with self.assertRaises(Exception) as exc_data:
            manager.create_load_balancer("tsuru")
        self.assertEqual(str(exc_data.exception), 'some error')
        cs_instance.make_request.assert_any_call('associateIpAddress', {
            'networkid': 'net-id',
            'projectid': 'proj-123',
            'zoneid': 'zone-id',
            'vpcid': 'vpc-id',
            'lbenvironmentid': 'env-id',
        }, response_key='associateipaddressresponse')
        cs_instance.make_request.assert_any_call('disassociateIpAddress', {
            'projectid': 'proj-123',
            'id': 'lb-ip-id',
        })
        cs_instance.createLoadBalancerRule.assert_called_with({
            'networkid': 'net-id',
            'algorithm': 'leastconn',
            'publicport': '80',
            'privateport': '8080',
            'openfirewall': 'false',
            'publicipid': 'lb-ip-id',
            'name': 'tsuru.abc.com',
            'additionalportmap': '81:8081,82:8082',
            'projectid': 'proj-123',
        })

    @mock.patch("hm.lb_managers.cloudstack.CloudStack")
    def test_attach_real(self, cs_mock):
        cs_instance = cs_mock.return_value
        cs_instance.make_request.return_value = {'jobid': 'j1'}
        cs_instance.assignToLoadBalancerRule.return_value = {'jobid': 'j2'}
        cs_instance.wait_for_job.return_value = {'jobresult': True}

        vms = {"virtualmachine": [{"id": "abc123", "nic": [{"id": "def456", "networkid": "netid1"}]}]}
        cs_instance.listVirtualMachines.return_value = vms

        lb = load_balancer.LoadBalancer('lbid', 'lbname', 'lbaddr', ip_id='ip_id', project_id='projid')
        h = host.Host('hostid', 'hostaddr')
        manager = cloudstack.CloudstackLB(self.conf)
        manager.attach_real(lb, h)
        cs_instance.make_request.assert_called_once_with('assignNetwork', {
            'id': 'lbid',
            'networkids': 'netid1',
            'projectid': 'projid',
        })
        cs_instance.assignToLoadBalancerRule.assert_called_once_with({
            'id': 'lbid',
            'projectid': 'projid',
            'virtualmachineids': 'hostid',
        })

    @mock.patch("hm.lb_managers.cloudstack.CloudStack")
    def test_detach_real(self, cs_mock):
        cs_instance = cs_mock.return_value
        cs_instance.removeFromLoadBalancerRule.return_value = {'jobid': 'j1'}
        lb = load_balancer.LoadBalancer('lbid', 'lbname', 'lbaddr', ip_id='ip_id', project_id='projid')
        h = host.Host('hostid', 'hostaddr')
        manager = cloudstack.CloudstackLB(self.conf)
        manager.detach_real(lb, h)
        cs_instance.removeFromLoadBalancerRule.assert_called_once_with({
            'id': 'lbid',
            'projectid': 'projid',
            'virtualmachineids': 'hostid',
        })
        cs_instance.wait_for_job.assert_called_with('j1', 100)

    @mock.patch("hm.lb_managers.cloudstack.CloudStack")
    def test_destroy_load_balancer(self, cs_mock):
        cs_instance = cs_mock.return_value
        cs_instance.deleteLoadBalancerRule.return_value = {'jobid': 'j1'}
        cs_instance.make_request.return_value = {'jobid': 'j2'}
        lb = load_balancer.LoadBalancer('lbid', 'lbname', 'lbaddr', ip_id='ipid', project_id='projid')
        manager = cloudstack.CloudstackLB(self.conf)
        manager.destroy_load_balancer(lb)
        cs_instance.deleteLoadBalancerRule.assert_called_once_with({
            'id': 'lbid',
            'projectid': 'projid',
        })
        cs_instance.make_request.assert_called_once_with('disassociateIpAddress', {
            'id': 'ipid',
            'projectid': 'projid',
        })
        cs_instance.wait_for_job.assert_any_call('j1', 100)
        cs_instance.wait_for_job.assert_any_call('j2', 100)
