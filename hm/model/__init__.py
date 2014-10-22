# Copyright 2014 hm authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.


def storage(conf=None):
    from hm.storage import MongoDBStorage
    return MongoDBStorage(conf)


class BaseModel(object):

    def storage(self):
        return storage(self.config)
