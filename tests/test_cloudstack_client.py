# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import base64
import unittest

import mock

from hm.iaas import cloudstack_client


class CloudStackClientTestCase(unittest.TestCase):

    def test_encode_user_data(self):
        client = cloudstack_client.CloudStack("http://localhost", "api_key", "secret!")
        expected = base64.b64encode("some user data")
        self.assertEqual(expected, client.encode_user_data("some user data"))

    def test_signature(self):
        client = cloudstack_client.CloudStack(
            "https://somewhere.com:443/client/api",
            "aaBB_1cC_JDSLkdjaskjLKSDJdlKDSJkldKDLSKdKsldjSKL_wDJKHSskjdshajkHDKJSHksjdhjsjsdjk_dsZ",
            "aaB-D1cCSJDSLkdjask-LKSDJdlKDSJ_ldKDLSKdKsldjSKLdwDJKHSskjdshajkHDKJSHksjdhjsjsdjkpdsZ")
        client.request({
            'command': 'createLBHealthCheckPolicy',
            'response': 'json',
            'lbruleid': '99999999-6eac-42fe-845f-814ba9e29d2a',
            'projectid': '11111111-3176-415f-8007-a47dc11ad8c6',
            'pingpath': 'GET /_nginx_healthcheck/',
        })
        self.assertEqual(
            client.value,
            'https://somewhere.com:443/client/api?'
            'apiKey=aaBB_1cC_JDSLkdjaskjLKSDJdlKDSJkldKDLSKdKsldjSKL_wDJKHSskjdshajkHDKJSHksjdhjsjsdjk_dsZ&'
            'command=createLBHealthCheckPolicy&'
            'lbruleid=99999999-6eac-42fe-845f-814ba9e29d2a&'
            'pingpath=GET+%2F_nginx_healthcheck%2F&'
            'projectid=11111111-3176-415f-8007-a47dc11ad8c6&'
            'response=json&'
            'signature=r73%2BEc%2FFSYKE0xB4qt3U37UYCsQ%3D'
        )

    @mock.patch('hm.iaas.cloudstack_client.urllib')
    def test_wait_for_job(self, urllib):
        client = cloudstack_client.CloudStack("http://localhost", "api_key", "secret!")
        urllib.quote_plus.side_effect = lambda x: x
        urllib.urlopen.return_value.read.return_value = '{"queryasyncjobresultresponse":{"jobstatus":1}}'
        client.wait_for_job('x', 3)
        urllib.urlopen.assert_called_once_with(
            'http://localhost?apiKey=api_key&command=queryAsyncJobResult'
            '&jobid=x&response=json&signature=glJwmvjkOcgmqZljJdlruU89Q0o=')

    @mock.patch('hm.iaas.cloudstack_client.urllib')
    def test_wait_for_job_timeout(self, urllib):
        client = cloudstack_client.CloudStack("http://localhost", "api_key", "secret!")
        urllib.quote_plus.side_effect = lambda x: x
        urllib.urlopen.return_value.read.return_value = '{"queryasyncjobresultresponse":{"jobstatus":0}}'
        with self.assertRaises(cloudstack_client.MaxTryWaitingForJobError) as cm:
            client.wait_for_job('x', 2)
        exc = cm.exception
        self.assertEqual(2, exc.max_tries)
        self.assertEqual("x", exc.job_id)
        self.assertEqual("exceeded 2 tries waiting for job x", str(exc))
        self.assertEqual(urllib.urlopen.call_count, 2)
        urllib.urlopen.assert_called_with(
            'http://localhost?apiKey=api_key&command=queryAsyncJobResult'
            '&jobid=x&response=json&signature=glJwmvjkOcgmqZljJdlruU89Q0o=')

    @mock.patch('hm.iaas.cloudstack_client.urllib')
    def test_wait_for_job_error_result(self, urllib):
        client = cloudstack_client.CloudStack("http://localhost", "api_key", "secret!")
        urllib.quote_plus.side_effect = lambda x: x
        urllib.urlopen.return_value.read.return_value = '{"queryasyncjobresultresponse":{"jobstatus":2}}'
        with self.assertRaises(Exception) as cm:
            client.wait_for_job('x', 3)
        exc = cm.exception
        self.assertEqual("async job error: {u'jobstatus': 2}", str(exc))
        self.assertEqual(urllib.urlopen.call_count, 1)
        urllib.urlopen.assert_called_with(
            'http://localhost?apiKey=api_key&command=queryAsyncJobResult'
            '&jobid=x&response=json&signature=glJwmvjkOcgmqZljJdlruU89Q0o=')
