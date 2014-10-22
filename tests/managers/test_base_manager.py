# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

import unittest

import mock

from hm import managers, config


class BaseManagerTestCase(unittest.TestCase):

    def test_get_user_data_txt(self):
        manager = managers.BaseManager({
            'USER_DATA_TXT': 'my user data'
        })
        data = manager.get_user_data()
        self.assertEqual(data, "my user data")

    @mock.patch('hm.managers.requests')
    def test_get_user_data_url(self, requests):
        manager = managers.BaseManager({
            'USER_DATA_URL': 'http://localhost/somewhere'
        })
        requests.get.return_value.status_code = 200
        requests.get.return_value.text = "user data from url"
        data = manager.get_user_data()
        self.assertEqual(data, "user data from url")
        requests.get.assert_called_with("http://localhost/somewhere")

    @mock.patch('hm.managers.requests')
    def test_get_user_data_url_error(self, requests):
        manager = managers.BaseManager({
            'USER_DATA_URL': 'http://localhost/somewhere'
        })
        requests.get.return_value.status_code = 500
        requests.get.return_value.text = "my error"
        with self.assertRaises(config.MissConfigurationError) as rsp:
            manager.get_user_data()
        self.assertEqual(str(rsp.exception),
                         "invalid user data response from http://localhost/somewhere: 500 - my error")
