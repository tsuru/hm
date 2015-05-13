# Copyright 2012 Kelcey Damage & Kraig Amador
# Source: http://goo.gl/KQUeMd

import base64
import hmac
import hashlib
import json
import urllib
import time

from hm import log


JOB_PENDING = 0
JOB_SUCCESS = 1
JOB_ERROR = 2


class CloudStack(object):

    def __init__(self, api_url, api_key, secret):
        self.api_url = api_url
        self.api_key = api_key
        self.secret = secret

    def encode_user_data(self, data):
        return base64.b64encode(data)

    def request(self, args):
        args["apiKey"] = self.api_key
        self.params = []
        self.sig_params = []
        self._sort_request(args)
        self._create_signature()
        self._build_post_request()

    def _sort_request(self, args):
        keys = sorted(args.keys())
        for key in keys:
            self.sig_params.append(
                key.lower() + "=" + urllib.quote_plus(args[key]).lower().replace('+', '%20'))
            self.params.append(key + "=" + urllib.quote_plus(args[key]))

    def _create_signature(self):
        self.query = "&".join(self.params)
        self.sig_query = "&".join(self.sig_params)
        digest = hmac.new(self.secret, msg=self.sig_query,
                          digestmod=hashlib.sha1).digest()
        self.signature = base64.b64encode(digest)

    def _build_post_request(self):
        self.query += "&signature=" + urllib.quote_plus(self.signature)
        self.value = self.api_url + "?" + self.query

    def __getattr__(self, name):
        def handler(*args, **kwargs):
            if kwargs:
                return self.make_request(name, kwargs)
            return self.make_request(name, args[0])
        return handler

    def _http_get(self, url):
        response = urllib.urlopen(url)
        return response.read()

    def make_request(self, command, args, response_key=None):
        args["response"] = "json"
        args["command"] = command
        self.request(args)
        data = self._http_get(self.value)
        key = command.lower() + "response"
        rsp_data = json.loads(data)
        response = rsp_data.get(key)
        if response is None and response_key:
            key = response_key
            response = rsp_data.get(key)
        if response is None or 'errorcode' in response:
            raise InvalidResponse("Invalid response running '{} {}': {}".format(command, args, data))
        log.debug("GET {}: {}".format(self.value, response))
        return response

    def wait_for_job(self, job_id, max_tries):
        status = JOB_PENDING
        tries = 0
        result = None
        while tries < max_tries:
            result = self.queryAsyncJobResult({"jobid": job_id})
            status = result["jobstatus"]
            if status != JOB_PENDING:
                break
            time.sleep(1)
            tries += 1
        if status == JOB_PENDING:
            raise MaxTryWaitingForJobError(max_tries, job_id)
        if status == JOB_ERROR:
            raise AsyncJobError("async job error: {}".format(result))
        return result


class AsyncJobError(Exception):
    pass


class InvalidResponse(Exception):
    pass


class MaxTryWaitingForJobError(Exception):

    def __init__(self, max_tries, job_id):
        self.max_tries = max_tries
        self.job_id = job_id
        msg = "exceeded {0} tries waiting for job {1}".format(max_tries, job_id)
        super(MaxTryWaitingForJobError, self).__init__(msg)
