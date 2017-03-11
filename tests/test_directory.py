import unittest
import random
import os

import common

class DirectoryTestCase(common.TestCase):
    def test_create_directory(self):
        self.random_dir()

    def test_create_directory_with_ttl(self):
        n = self.client.directory.create(self.random_key('/ttldir_'), ttl=60)

    def test_delete_if_index(self):
        # Make base directory
        n = self.random_dir()

        # Make a child
        child_key = os.path.join(n.key, 'key1')
        self.client.node.set(child_key, 1)

        # Intentionally fail a couple deletes
        n2 = self.client.directory.delete_if_index(n.key, n.modified_index + 999)
        n3 = self.client.directory.delete_if_index(n.key, n.modified_index - 1)
        
        # Check the directory and child are intact
        n4 = self.client.directory.list(n.key)
        self.assertTrue(n4.is_directory)
        self.assertIsNotNone(n4.children)
        self.assertEqual(n4.children[0].key, child_key)

        # Perform the delete properly
        n5 = self.client.directory.delete_if_index(n.key, n.modified_index)
        n6 = self.client.directory.list(n.key)
        self.assertFalse(n6.value)

    
    def test_children(self):        
        n = self.random_dir()
        c = ['key1','key2', 'key4', 'key5', 'key3']
        def create_child(name):
            self.client.node.set(os.path.join(n.key, name), name)
        map(create_child, c)
        n = self.client.directory.list(n.key)
        self.assert_(n.children)
        self.assertEqual(len(n.children), 5)

        n = self.client.directory.list(n.key, sorted=True)
        self.assert_(n.children)
        self.assertEqual(len(n.children), 5)
        self.assertEqual(os.path.split(n.children[0].key)[-1], 'key1')
        self.assertEqual(os.path.split(n.children[4].key)[-1], 'key5')

        self.client.directory.delete_recursive(n.key) 
        
    def test_delete(self):
        n = self.random_dir()
        self.client.directory.delete(n.key)

    def test_delete_recursive(self):
        n = self.random_dir()
        n2 = self.random_dir(n.key + '/')
        n3 = self.random_dir(n2.key + '/')
        n4 = self.random_dir(n3.key + '/')

        n = self.client.directory.list(n.key, recursive=True)
        self.assertTrue(n.is_directory)
        self.assertEqual(len(n.children), 1)

        c2 = n.children[0]
        self.assertTrue(c2.is_directory)
        self.assertEqual(c2.key, n2.key)
        self.assertEqual(len(c2.children), 1)

        c3 = c2.children[0]
        self.assertTrue(c3.is_directory)
        self.assertEqual(c3.key, n3.key)
        self.assertEqual(len(c3.children), 1)

        c4 = c3.children[0]
        self.assertTrue(c4.is_directory)
        self.assertEqual(c4.key, n4.key)
        self.assertEqual(len(c4.children), 0)

        self.client.directory.delete_recursive(n.key)
        
        n4 = self.client.node.get(n4.key)
        self.assertIsNone(n4.value)
        self.assertTrue(n4.is_deleted)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(DirectoryTestCase)
