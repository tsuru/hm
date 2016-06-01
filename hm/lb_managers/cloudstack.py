# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import sys

from hm import lb_managers, log
from hm.model import load_balancer
from hm.iaas.cloudstack_client import CloudStack, AsyncJobError


class CloudstackLB(lb_managers.BaseLBManager):

    def __init__(self, config=None):
        super(CloudstackLB, self).__init__(config)
        url = self.get_conf("CLOUDSTACK_API_URL")
        key = self.get_conf("CLOUDSTACK_API_KEY")
        secret_key = self.get_conf("CLOUDSTACK_SECRET_KEY")
        self.cs_client = CloudStack(url, key, secret_key)
        self.async_max_tries = int(self.get_conf("CLOUDSTACK_MAX_TRIES", 100))
        self.project_id = self.get_conf("CLOUDSTACK_PROJECT_ID", None)
        self.associate_ip_command = self.get_conf("CLOUDSTACK_LB_ASSOCIATE_IP_COMMAND", "associateIpAddress")
        self.disassociate_ip_command = self.get_conf("CLOUDSTACK_LB_DISASSOCIATE_IP_COMMAND",
                                                     "disassociateIpAddress")
        self.assign_network_command = self.get_conf("CLOUDSTACK_LB_ASSIGN_NETWORK_COMMAND", None)
        self.lb_network_id = self.get_conf("CLOUDSTACK_LB_NETWORK_ID")
        self.lb_zone_id = self.get_conf("CLOUDSTACK_LB_ZONE_ID", None)
        self.lb_vpc_id = self.get_conf("CLOUDSTACK_LB_VPC_ID", None)
        self.lb_environment_id = self.get_conf("CLOUDSTACK_LB_ENVIRONMENT_ID", None)
        self.lb_algorithm = self.get_conf("CLOUDSTACK_LB_ALGORITHM", "leastconn")
        self.lb_port_mapping = self.get_conf("CLOUDSTACK_LB_PORT_MAPPING")
        self.lb_open_firewall = self.get_conf("CLOUDSTACK_LB_OPEN_FIREWALL", "false")
        self.lb_healthcheck = self.get_conf("CLOUDSTACK_LB_HEALTHCHECK", None)
        self.lb_network_index = int(self.get_conf("CLOUDSTACK_LB_NETWORK_INDEX", 0))
        self.lb_domain = self.get_conf("CLOUDSTACK_LB_DOMAIN", None)
        self.lb_cache_group = self.get_conf("CLOUDSTACK_LB_CACHE_GROUP", None)

    def create_load_balancer(self, name):
        ip_id = self._associate_ip()
        try:
            lb_id, address = self._create_lb_rule(ip_id, name)
            self._assign_lb_additional_networks(lb_id)
            try:
                self._create_lb_hc(lb_id)
            except:
                exc_info = sys.exc_info()
                try:
                    self._delete_lb_rule(lb_id, self.project_id)
                except:
                    log.exception('error in rollback trying to delete lb rule')
                raise exc_info[0], exc_info[1], exc_info[2]

            return load_balancer.LoadBalancer(
                lb_id, name, address,
                project_id=self.project_id,
                ip_id=ip_id)
        except:
            exc_info = sys.exc_info()
            try:
                self._dissociate_ip(ip_id, self.project_id)
            except:
                log.exception('error in rollback trying to dissociate ip')
            raise exc_info[0], exc_info[1], exc_info[2]

    def destroy_load_balancer(self, lb):
        self._delete_lb_rule(lb.id, lb.project_id)
        self._dissociate_ip(lb.ip_id, lb.project_id)

    def attach_real(self, lb, host):
        list_params = {
            "id": host.id,
        }
        network_params = {
            "id": lb.id,
        }
        assign_params = {
            'id': lb.id,
            'virtualmachineids': host.id,
        }
        if hasattr(lb, 'project_id'):
            list_params["projectid"] = lb.project_id
            network_params["projectid"] = lb.project_id
            assign_params['projectid'] = lb.project_id
        if self.assign_network_command:
            vms = self.cs_client.listVirtualMachines(list_params)["virtualmachine"]
            nic = vms[0]["nic"][self.lb_network_index]
            network_params["networkids"] = nic["networkid"]
            net_rsp = self.cs_client.make_request(self.assign_network_command, network_params)
            try:
                self._wait_if_jobid(net_rsp)
            except AsyncJobError:
                log.exception('ignored error assigning network to lb')
        rsp = self.cs_client.assignToLoadBalancerRule(assign_params)
        self._wait_if_jobid(rsp)

    def detach_real(self, lb, host):
        params = {
            'id': lb.id,
            'virtualmachineids': host.id,
        }
        if hasattr(lb, 'project_id'):
            params['projectid'] = lb.project_id
        rsp = self.cs_client.removeFromLoadBalancerRule(params)
        self._wait_if_jobid(rsp)

    def _associate_ip(self):
        ip_params = {
            'networkid': self.lb_network_id
        }
        if self.project_id:
            ip_params['projectid'] = self.project_id
        if self.lb_zone_id:
            ip_params['zoneid'] = self.lb_zone_id
        if self.lb_vpc_id:
            ip_params['vpcid'] = self.lb_vpc_id
        if self.lb_environment_id:
            ip_params['lbenvironmentid'] = self.lb_environment_id
        ip_rsp = self.cs_client.make_request(self.associate_ip_command,
                                             ip_params,
                                             response_key="associateipaddressresponse")
        self._wait_if_jobid(ip_rsp)
        return ip_rsp['id']

    def _create_lb_rule(self, ip_id, name):
        public, private, additional = self._slit_ports()
        if self.lb_domain:
            name = '{}.{}'.format(name, self.lb_domain)
        lb_params = {
            'networkid': self.lb_network_id,
            'algorithm': self.lb_algorithm,
            'publicport': public,
            'privateport': private,
            'openfirewall': self.lb_open_firewall,
            'publicipid': ip_id,
            'name': name,
        }
        if additional:
            lb_params['additionalportmap'] = additional
        if self.project_id:
            lb_params['projectid'] = self.project_id
        if self.lb_cache_group:
            lb_params['cache'] = self.lb_cache_group
        lb_rsp = self.cs_client.createLoadBalancerRule(lb_params)
        result = self._wait_if_jobid(lb_rsp)
        return lb_rsp['id'], result['loadbalancer']['publicip']

    def _assign_lb_additional_networks(self, lb_id):
        network_ids = []
        i = 0
        while True:
            try:
                id = self.get_conf("CLOUDSTACK_LB_NETWORK_ID_%s" % i)
                i += 1
                if not id:
                    break
                if id == self.lb_network_id:
                    continue
                network_ids.append(id)
            except:
                break
        if not network_ids:
            return
        assign_networks_params = {
            "projectid": self.project_id,
            "id": lb_id,
            "networkids": ",".join(network_ids),
        }
        lb_rsp = self.cs_client.assignNetworksToLoadBalancerRule(assign_networks_params)
        self._wait_if_jobid(lb_rsp)

    def _create_lb_hc(self, lb_id):
        if not self.lb_healthcheck:
            return
        hc_params = {
            'lbruleid': lb_id,
            'pingpath': self.lb_healthcheck,
        }
        if self.project_id:
            hc_params['projectid'] = self.project_id
        hc_rsp = self.cs_client.createLBHealthCheckPolicy(hc_params)
        self._wait_if_jobid(hc_rsp)

    def _slit_ports(self):
        ports = self.lb_port_mapping.split(',')
        if len(ports) == 0:
            raise Exception("no port mapping defined in CLOUDSTACK_LB_PORT_MAPPING")
        mapping_parts = ports[0].split(':')
        if len(mapping_parts) != 2:
            raise Exception("invalid port mapping format in CLOUDSTACK_LB_PORT_MAPPING")
        return mapping_parts[0], mapping_parts[1], ','.join(ports[1:])

    def _wait_if_jobid(self, rsp):
        if 'jobid' not in rsp:
            return rsp
        job_result = self.cs_client.wait_for_job(rsp['jobid'], self.async_max_tries)
        return job_result['jobresult']

    def _delete_lb_rule(self, lb_id, project_id):
        lb_params = {
            'id': lb_id,
        }
        if project_id:
            lb_params['projectid'] = project_id
        lb_rsp = self.cs_client.deleteLoadBalancerRule(lb_params)
        self._wait_if_jobid(lb_rsp)

    def _dissociate_ip(self, ip_id, project_id):
        ip_params = {
            'id': ip_id,
        }
        if project_id:
            ip_params['projectid'] = project_id
        ip_rsp = self.cs_client.make_request(self.disassociate_ip_command, ip_params)
        self._wait_if_jobid(ip_rsp)


lb_managers.register('cloudstack', CloudstackLB)
