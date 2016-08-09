# Copyright 2015 hm authors. All rights reserved.
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

    def create_host(self, name=None, alternative_id=0):
        group = self.get_conf("CLOUDSTACK_GROUP", "")
        user_data = self.get_user_data()
        if group and name:
            name = "{}_{}".format(group, name)
        elif not name:
            name = group
        data = {
            "group": group,
            "displayname": name,
            "templateid": self._get_alternate_conf("CLOUDSTACK_TEMPLATE_ID", alternative_id),
            "zoneid": self._get_alternate_conf("CLOUDSTACK_ZONE_ID", alternative_id),
            "serviceofferingid": self._get_alternate_conf("CLOUDSTACK_SERVICE_OFFERING_ID", alternative_id),
        }
        if user_data:
            data["userdata"] = self.client.encode_user_data(user_data)
        project_id = self._get_alternate_conf("CLOUDSTACK_PROJECT_ID", alternative_id, None)
        if project_id:
            data["projectid"] = project_id
        network_ids = self._get_alternate_conf("CLOUDSTACK_NETWORK_IDS", alternative_id, None)
        if network_ids:
            data["networkids"] = network_ids
        vm_job = self.client.deployVirtualMachine(data)
        max_tries = int(self.get_conf("CLOUDSTACK_MAX_TRIES", 100))
        if not vm_job.get("jobid"):
            raise CloudStackException(
                "unexpected response from deployVirtualMachine({}), expected jobid key, got: {}".format(
                    repr(data), repr(vm_job)))
        vm = self._wait_for_unit(vm_job, max_tries, project_id)
        tags = self.get_conf("HOST_TAGS", "")
        if tags:
            self._tag_vm(tags.split(","), vm, project_id)
        return host.Host(id=vm["id"], dns_name=self._get_dns_name(vm), alternative_id=alternative_id)

    def _tag_vm(self, tag_list, vm, project_id=None):
        params = {}

        for i, tag in enumerate(tag_list, start=1):
            parts = tag.split(":", 2)
            if len(parts) < 2:
                continue
            key, value = parts
            params["tags[{}].key".format(i)] = key
            params["tags[{}].value".format(i)] = value

        if not params:
            return

        params.update({"resourcetype": "UserVm", "resourceids": vm["id"]})
        if project_id:
            params["projectid"] = project_id
        self.client.createTags(params)

    def destroy_host(self, host_id):
        self.client.destroyVirtualMachine({"id": host_id})

    def start_host(self, host_id):
        self.client.startVirtualMachine({"id": host_id})

    def stop_host(self, host_id, forced=False):
        self.client.stopVirtualMachine({"id": host_id, "forced": forced})

    def restore_host(self, host_id):
        self.client.make_request('restoreVirtualMachine', {'virtualmachineid': host_id},
                                 response_key='restorevmresponse')

    def _get_dns_name(self, vm):
        if not vm.get("nic"):
            return ""
        network_index = int(self.get_conf("CLOUDSTACK_PUBLIC_NETWORK_INDEX", 0))
        dns_name = vm["nic"][network_index]["ipaddress"]
        return dns_name

    def _wait_for_unit(self, vm_job, max_tries, project_id):
        self.client.wait_for_job(vm_job["jobid"], max_tries)
        data = {"id": vm_job["id"]}
        if project_id:
            data["projectid"] = project_id
        vms = self.client.listVirtualMachines(data)
        return vms["virtualmachine"][0]

    def _get_alternate_conf(self, name, alternative_id, default=None):
        env_var = "{}_{}".format(name, alternative_id)
        val = self.get_conf(env_var, default)
        if val is not None:
            return val
        return self.get_conf(name, default)


class CloudStackException(Exception):
    pass


managers.register('cloudstack', CloudStackManager)
