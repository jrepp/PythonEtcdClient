import unittest
import random
import etcd.errors

import common

class WaitTestCase(common.TestCase):
    def test_wait(self):
        n = self.random_node()
        self.client.wait(n.key)


    def test_wait_recursive(self):    
        n = self.random_dir('/wait_recursive')
        n2 = self.random_dir('/wait_recursive/child_dir')
        n3 = self.client.node.set(n2.key + '/key', 1)
        w = n.wait(n.key) 
        self.client.node.set(n3.key, 2)

    def test_wait_consistent(self):
        n = self.random_key('/wait_consistent')
        w = n.wait(n.key)
        self.client.node.set(n.key, 3)
