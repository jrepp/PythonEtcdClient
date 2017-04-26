import unittest
import random
import etcd

import common

class HighLevelTestCase(common.TestCase):
    def test_basic(self):
        # Setup the tree
        d = self.random_dir()
        n20 = self.client.node.set('{}/subkey1'.format(d.key), 20)
        n30 = self.client.node.set('{}/subkey2'.format(d.key), 30)
        sub = self.random_dir('{}/'.format(d.key))
        n40 = self.client.node.set('{}/subkey3'.format(sub.key), 40)
        self.assertEqual(int(n20.value), 20)
        self.assertEqual(int(n30.value), 30)
        self.assertEqual(int(n40.value), 40)

        # Use the hl operations 
        etcd.use(self.client)
        nodes = etcd.ls()
        self.assertEqual(len(nodes), 3)
        r = etcd.cd(sub.key.split('/')[-1])
        self.assertEqual(r, sub.key)
        v = etcd.get('subkey3')
        self.assertEqual(v, 40)

    
def suite():
    return unittest.TestLoader().loadTestsFromTestCase(HighLevelTestCase)

