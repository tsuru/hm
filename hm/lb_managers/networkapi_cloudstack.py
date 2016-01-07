# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from hm import lb_managers, log
from hm.model import load_balancer
from hm.iaas.cloudstack_client import CloudStack

network_api_available = True
try:
    from networkapiclient import EnvironmentVIP, Ip, Vip
    from networkapiclient.exception import IpNaoExisteError
except ImportError:
    network_api_available = False


class NetworkApiCloudstackLB(lb_managers.BaseLBManager):

    def __init__(self, config=None):
        super(NetworkApiCloudstackLB, self).__init__(config)
        url = self.get_conf("CLOUDSTACK_API_URL")
        key = self.get_conf("CLOUDSTACK_API_KEY")
        secret_key = self.get_conf("CLOUDSTACK_SECRET_KEY")
        self.cs_client = CloudStack(url, key, secret_key)

        self.networkapi_endpoint = self.get_conf("NETWORKAPI_ENDPOINT")
        self.networkapi_user = self.get_conf("NETWORKAPI_USER")
        self.networkapi_password = self.get_conf("NETWORKAPI_PASSWORD")
        self.create_project_id = self.get_conf("CLOUDSTACK_PROJECT_ID", None)
        self.vip_network_index = int(self.get_conf("CLOUDSTACK_VIP_NETWORK_INDEX", 0))
        self.vip_config = VIPConfig(
            environment_p44=self.get_conf("NETWORKAPI_AMBIENTE_P44_TXT"),
            client=self.get_conf("NETWORKAPI_CLIENTE_TXT"),
            finality=self.get_conf("NETWORKAPI_FINALIDADE_TXT"),
            healthcheck=self.get_conf("VIP_HEALTHCHECK", "GET / HTTP/1.1\r\n\r\n"),
            healthcheck_expect=self.get_conf("VIP_HEALTHCHECK_EXPECT", 26),
            lb_method=self.get_conf("VIP_METHOD_BAL", "least-conn"),
            persistence=self.get_conf("VIP_PERSISTENCE", "(nenhum)"),
            cache=self.get_conf("VIP_CACHE", "(nenhum)"),
            maxconn=self.get_conf("VIP_MAXCONN", "1000"),
            business_area=self.get_conf("VIP_BUSINESS_AREA", ""),
            service_name=self.get_conf("VIP_SERVICE_NAME", ""),
            port_mapping=self.get_conf("VIP_PORT_MAPPING").split(',')
        )

    def create_load_balancer(self, name):
        vip_id, ip_id, address = self._create_vip(name, self.vip_config)

        return load_balancer.LoadBalancer(
            vip_id, name, address,
            ip_id=ip_id,
            project_id=self.create_project_id)

    def destroy_load_balancer(self, lb):
        data = {
            "vipid": lb.id
        }
        if hasattr(lb, 'project_id'):
            data["projectid"] = lb.project_id
        self.cs_client.removeGloboNetworkVip(data)
        return self._remove_vip(lb)

    def attach_real(self, lb, host):
        real_data, network_data = self._get_association_data(lb, host)
        self.cs_client.addGloboNetworkVipToAccount(network_data)
        self.cs_client.associateGloboNetworkRealToVip(real_data)

    def detach_real(self, lb, host):
        real_data, _ = self._get_association_data(lb, host)
        self.cs_client.disassociateGloboNetworkRealFromVip(real_data)

    def _get_association_data(self, lb, host):
        real_data = {"vipid": lb.id}
        network_data = {"vipid": lb.id}
        list_data = {"id": host.id}

        if getattr(lb, 'project_id', None):
            list_data["projectid"] = \
                real_data["projectid"] = \
                network_data["projectid"] = lb.project_id
        vms = self.cs_client.listVirtualMachines(list_data)["virtualmachine"]
        nic = vms[0]["nic"][self.vip_network_index]

        real_data["nicid"] = nic["id"]
        network_data["networkid"] = nic["networkid"]
        return real_data, network_data

    def _remove_vip(self, lb):
        client_vip = Vip.Vip(
            self.networkapi_endpoint, self.networkapi_user,
            self.networkapi_password)
        client_vip.remove_script(lb.id)
        client_vip.remover(lb.id)
        try:
            client_ip = Ip.Ip(self.networkapi_endpoint, self.networkapi_user,
                              self.networkapi_password)
            client_ip.delete_ip4(lb.ip_id)
        except IpNaoExisteError:
            pass

    def _create_vip(self, name, vip_config):
        vip_id = None
        client_evip = EnvironmentVIP.EnvironmentVIP(
            self.networkapi_endpoint,
            self.networkapi_user,
            self.networkapi_password)
        evip = client_evip.search(ambiente_p44_txt=vip_config.environment_p44,
                                  cliente_txt=vip_config.client,
                                  finalidade_txt=vip_config.finality)
        client_ip = Ip.Ip(self.networkapi_endpoint, self.networkapi_user,
                          self.networkapi_password)
        vip_ip = client_ip.get_available_ip4_for_vip(evip["environment_vip"]["id"],
                                                     u"tsuru hm {0}".format(name))
        try:
            client_vip = Vip.Vip(self.networkapi_endpoint, self.networkapi_user,
                                 self.networkapi_password)
            request = client_vip.add(id_ipv4=vip_ip["ip"]["id"],
                                     id_ipv6=None,
                                     id_healthcheck_expect=vip_config.healthcheck_expect,
                                     finality=vip_config.finality,
                                     client=vip_config.client,
                                     environment=vip_config.environment_p44,
                                     cache=vip_config.cache,
                                     method_bal=vip_config.lb_method,
                                     persistence=vip_config.persistence,
                                     healthcheck_type=u"HTTP",
                                     healthcheck=vip_config.healthcheck,
                                     timeout="5",
                                     host="{0}.hm.tsuru".format(name),
                                     maxcon=vip_config.maxconn,
                                     areanegocio=vip_config.business_area,
                                     nome_servico=vip_config.service_name,
                                     l7_filter=None,
                                     reals=[],
                                     reals_prioritys=[],
                                     reals_weights=[],
                                     ports=vip_config.port_mapping)
            vip_id = request["requisicao_vip"]["id"]
            log.debug(u"VIP request %s successfully created." % vip_id)
            client_vip.validate(vip_id)
            client_vip.criar(vip_id)
            address = "{oct1}.{oct2}.{oct3}.{oct4}".format(**vip_ip["ip"])
            return vip_id, vip_ip["ip"]["id"], address
        except Exception as e:
            if vip_id:
                try:
                    client_vip.remove_script(vip_id)
                    client_vip.remover(vip_id)
                except Exception as exc:
                    args = [str(a) for a in exc.args]
                    error = "".join(args)
                    log.error("Failed to remove the VIP {0}: {1}".format(vip_id, error))
            client_ip.delete_ip4(vip_ip["ip"]["id"])
            raise e


class VIPConfig(object):
    environment_p44 = None
    client = None
    finality = None
    healthcheck = None
    healthcheck_expect = None
    cache = None
    lb_method = None
    persistence = None
    maxconn = None
    business_area = None
    service_name = None
    port_mapping = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            self.__setattr__(k, v)


if network_api_available:
    lb_managers.register('networkapi_cloudstack', NetworkApiCloudstackLB)
