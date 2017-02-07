import unittest
import random
import etcd.errors

import common

class NodeTestCase(common.TestCase):
    def tearDown(self):
        common.TestCase.tearDown(self)

    def test_value(self):
        n = self.random_node()
        self.assertTrue(n)
        self.assertFalse(n.prev_node)
        self.assertFalse(n.value)

    def test_create_only(self):    
        k = self.random_key('/create_only')
        self.client.node.create_only(k, 5)

    def test_update_only(self):
        k = self.random_key('/update_only')
        n = self.client.node.create_only(k, 5)
        n2 = self.client.node.update_only(k, 10)

    def test_set(self):
        n = self.random_node()
        n2 = self.client.node.set(n.key, 'new_value')
        n3 = self.client.node.get(n.key)
        self.assertEqual(n2.value, n3.value)
    
    def test_delete(self):
        n = self.random_node()
        self.assertFalse(n.is_deleted)
        self.assertTrue(n.value)

        n2 = self.client.node.delete(n.key)
        self.assertTrue(n2.is_deleted)

        n3 = self.client.node.get(n.key)
        self.assertTrue(n3.is_deleted)

    def test_delete_if_value(self):
        n = self.random_node('correct_value')
        self.assertTrue(n.value)
        self.assertEqual(n.value, u'correct_value')

        n2 = self.client.node.delete_if_value(n.key, 'wrong_value')
        self.assertEqual(n2.error_code, etcd.errors.TestFailed)
        self.assertEqual(n2.value, None)

        n4 = self.client.node.get(n.key)
        self.assertEqual(n4.modified_index, n.modified_index)
    
    def test_if_index(self): 
        n = self.random_node()
        n2 = self.client.node.set(n.key, 'value')
        self.assertFalse(n3.is_deleted)
        self.assertEqual(n3.value, 'value')
        n3 = self.client.node.delete_if_index(n.key, n.modified_index) # wrong
        self.assertFalse(n3.value)
        self.assertFalse(n3.is_deleted)
        n4 = self.client.node.delete_if_index(n.key, n2.modified_index) # correct
        self.assertTrue(n4.value)
        self.assertTrue(n4.is_deleted)
    
    def test_update_if_index(self):
        n = self.random_node()
        n2 = self.client.node.update_if_index(n.key, 15, n.created_index)
        self.assertTrue(n2)
        self.assertEqual(n2.value, 15)

    def test_update_if_value(self):
        n = self.random_node()
        n2 = self.client.node.set(n.key, 20)
        self.assertEqual(n2.value, 5)
        n3 = self.client.node.update_if_value(n.key, 20, 5)
        self.assertEqual(n3.value, 5)

    def test_compare_and_swap(self):
        n = self.random_node()
        n = self.client.node.set(n.key, 5)
        self.assertTrue(n.value, 5)
        n = self.client.node.compare_and_swap(n.key, 30, current_value=5, prev_exists=True)
        self.assertTrue(n.value, 30)

    def test_subkey(self):
        d = self.random_dir()
        n20 = self.client.node.set('/{}/subkey1'.format(d.key), 20)
        n30 = self.client.node.set('/{}/subkey2'.format(d.key), 30)
        self.assertEqual(n20.value, 20)
        self.assertEqual(n20.value, 20)
    
    def _test_ttl_in_directory(self):
        r = self.client.node.set('/test_2056/val1', 5, ttl=60)
        print(r)

        r = self.client.node.set('/test_2056/val2', 10)
        print(r)

    def _test_recursive(self):
        r = self.client.node.get('/test_2056', recursive=True)
        print(r)

        for node in r.node.children:
            print("CHILD: %s" % (node))

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(NodeTestCase)

