import unittest
import random

import common

class DirectoryTestCase(common.TestCase):
    def test_create_directory(self):
        dirname = '/dir_test{}'.format(random.randint())
        r = self.client.directory.create(dirname)
        print(r)

    def test_create_directory_with_ttl(self):
        r = self.client.directory.create('/test_2056/new_dir', ttl=60)

    def test_delete_if_index(self):            
        r = self.client.directory.delete_if_index('/dir_test/bb', r.node.modified_index + 999)
        print(r)

    
    def test_children(self):        
        pass
    
    def test_delete(self):
        pass

    def test_delete_recursive(self):
        r = self.client.directory.delete_recursive('/test_2056')
        print(r)

        r = self.client.node.set('/test_2056/dir1/val11', 20)

def suite():
    return unittest.TestLoader().loadTestsFromTestCase(DirectoryTestCase)
