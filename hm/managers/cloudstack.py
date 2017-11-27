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
        self.max_tries = int(self.get_conf("CLOUDSTACK_MAX_TRIES", 100))

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
        if not vm_job.get("jobid"):
            raise CloudStackException(
                "unexpected response from deployVirtualMachine({}), expected jobid key, got: {}".format(
                    repr(data), repr(vm_job)))
        vm = self._wait_for_unit(vm_job, project_id)
        tags = self.get_conf("HOST_TAGS", "")
        if tags:
            self.tag_vm(tags.split(","), vm["id"], project_id)
        return host.Host(id=vm["id"], dns_name=self._get_dns_name(vm), alternative_id=alternative_id)

    def tag_vm(self, tag_list, vm_id, project_id=None):
        list_tags_params = {"resourcetype": "UserVm", "resourceid": vm_id}
        delete_tags_params = {"resourcetype": "UserVm", "resourceids": vm_id}
        add_tags_params = {"resourcetype": "UserVm", "resourceids": vm_id}
        if project_id:
            list_tags_params['projectid'] = project_id
            add_tags_params["projectid"] = project_id
            delete_tags_params['projectid'] = project_id
        machine_tags = self.client.listTags(list_tags_params)
        tag_add_count = 0
        tag_del_count = 0
        for tag in tag_list:
            ignore_tag_key = False
            parts = tag.split(":", 1)
            if len(parts) < 2:
                continue
            key, value = parts
            if 'tag' in machine_tags:
                for m_tag in machine_tags['tag']:
                    if key == m_tag['key'] and value != m_tag['value']:
                        delete_tags_params.update({"tags[{}].key".format(tag_del_count): m_tag['key'],
                                                   "tags[{}].value".format(tag_del_count): m_tag['value']})
                        tag_del_count += 1
                    if key == m_tag['key'] and value == m_tag['value']:
                        ignore_tag_key = True
            if value is not '' and not ignore_tag_key:
                add_tags_params["tags[{}].key".format(tag_add_count)] = key
                add_tags_params["tags[{}].value".format(tag_add_count)] = value
                tag_add_count += 1
        if any(item.startswith('tags') for item in delete_tags_params.keys()):
            job = self.client.deleteTags(delete_tags_params)
            self.client.wait_for_job(job["jobid"], self.max_tries)
        if not any(item.startswith('tags') for item in add_tags_params.keys()):
            return
        self.client.createTags(add_tags_params)

    def destroy_host(self, host_id):
        self.client.destroyVirtualMachine({"id": host_id})

    def start_host(self, host_id):
        self.client.startVirtualMachine({"id": host_id})

    def stop_host(self, host_id, forced=False):
        self.client.stopVirtualMachine({"id": host_id, "forced": forced})

    def restore_host(self, host_id, reset_template=False, reset_tags=False, alternative_id=0):
        restore_args = {'virtualmachineid': host_id}
        list_tags_params = {"resourcetype": "UserVm", "resourceid": host_id}
        project_id = self._get_alternate_conf("CLOUDSTACK_PROJECT_ID", 0, None)
        if project_id:
            list_tags_params['projectid'] = project_id
        tags = None
        if reset_template:
            template_id = self._get_alternate_conf("CLOUDSTACK_TEMPLATE_ID", alternative_id)
            restore_args['templateid'] = template_id
        if reset_tags:
            tags = self.get_conf("HOST_TAGS", "")
            if tags:
                current_tags = self.client.listTags(list_tags_params)
                if 'tag' in current_tags:
                    self.tag_vm(tags.split(","), host_id, project_id)
                else:
                    raise CloudStackException('''unexpected response from listTags on restore_host: {}
                                              '''.format(current_tags))
        try:
            vm_job = self.client.make_request('restoreVirtualMachine', restore_args,
                                              response_key='restorevmresponse')
            self._wait_for_unit(vm_job, project_id)
        except Exception as e:
            if reset_tags and tags:
                current_tags = ["{}:{}".format(tag['key'], tag['value']) for tag in current_tags['tag']]
                self.tag_vm(current_tags, host_id, project_id)
            raise CloudStackException(
                "unexpected response from restoreVirtualMachine({}), expected jobid key, got: {} ({})".format(
                    repr(restore_args), repr(vm_job), repr(e)))

    def _get_dns_name(self, vm):
        if not vm.get("nic"):
            return ""
        network_index = int(self.get_conf("CLOUDSTACK_PUBLIC_NETWORK_INDEX", 0))
        dns_name = vm["nic"][network_index]["ipaddress"]
        return dns_name

    def _wait_for_unit(self, vm_job, project_id):
        result = self.client.wait_for_job(vm_job["jobid"], self.max_tries)
        if vm_job.get("id"):
            data = {"id": vm_job["id"]}
        else:
            data = {"id": result['jobresult']['virtualmachine']['id']}
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
