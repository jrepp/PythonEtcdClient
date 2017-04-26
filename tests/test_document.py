import simplejson
import unittest
import random
import etcd.errors

import common

class DocumentTestCase(common.TestCase):
    def test_nested_doc(self):
        d = self.random_dir()
        n20 = self.client.node.set('{}/subkey1'.format(d.key), 20)
        n30 = self.client.node.set('{}/subkey2'.format(d.key), 30)
        sub = self.random_dir('{}/'.format(d.key))
        n40 = self.client.node.set('{}/subkey3'.format(sub.key), 40)
        self.assertEqual(int(n20.value), 20)
        self.assertEqual(int(n30.value), 30)
        self.assertEqual(int(n40.value), 40)
        doc = self.client.directory.document(d.key)
        json_str = simplejson.dumps(doc)
        doc2 = simplejson.loads(json_str)
    
def suite():
    return unittest.TestLoader().loadTestsFromTestCase(DocumentTestCase)

