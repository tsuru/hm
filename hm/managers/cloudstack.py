# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from hm import managers
from hm.model import host
from hm.iaas.cloudstack_client import CloudStack


class CloudStackManager(managers.BaseManager):

    def __init__(self, config=None):
        super(CloudStackManager, self).__init__(config)
        url = self.get_conf("CLOUDSTACK_API_URL")
        key = self.get_conf("CLOUDSTACK_API_KEY")
        secret_key = self.get_conf("CLOUDSTACK_SECRET_KEY")
        self.client = CloudStack(url, key, secret_key)

    def create_host(self):
        group = self.get_conf("CLOUDSTACK_GROUP", "")
        user_data = self.get_user_data()
        data = {
            "group": group,
            "templateid": self.get_conf("CLOUDSTACK_TEMPLATE_ID"),
            "zoneid": self.get_conf("CLOUDSTACK_ZONE_ID"),
            "serviceofferingid": self.get_conf("CLOUDSTACK_SERVICE_OFFERING_ID"),
        }
        if user_data:
            data["userdata"] = self.client.encode_user_data(user_data)
        project_id = self.get_conf("CLOUDSTACK_PROJECT_ID", None)
        if project_id:
            data["projectid"] = project_id
        network_ids = self.get_conf("CLOUDSTACK_NETWORK_IDS", None)
        if network_ids:
            data["networkids"] = network_ids
        vm_job = self.client.deployVirtualMachine(data)
        max_tries = int(self.get_conf("CLOUDSTACK_MAX_TRIES", 100))
        vm = self._wait_for_unit(vm_job, max_tries, project_id)
        return host.Host(id=vm["id"], dns_name=self._get_dns_name(vm))

    def destroy_host(self, host_id):
        self.client.destroyVirtualMachine({"id": host_id})

    def _get_dns_name(self, vm):
        if not vm.get("nic"):
            return ""
        network_name = self.get_conf("CLOUDSTACK_PUBLIC_NETWORK_NAME", None)
        dns_name = vm["nic"][-1]["ipaddress"]
        if network_name:
            for nic in vm["nic"]:
                if nic["networkname"] == network_name:
                    dns_name = nic["ipaddress"]
                    break
        return dns_name

    def _wait_for_unit(self, vm_job, max_tries, project_id):
        self.client.wait_for_job(vm_job["jobid"], max_tries)
        data = {"id": vm_job["id"]}
        if project_id:
            data["projectid"] = project_id
        vms = self.client.listVirtualMachines(data)
        return vms["virtualmachine"][0]


managers.register('cloudstack', CloudStackManager)
