import unittest
import random

from etcd.client import Client

class TestCase(unittest.TestCase):
    def setUp(self):
        self.client = Client(host='127.0.0.1', port=2379)

        # Track nodes for cleanup
        self.nodes = []

    def tearDown(self):
        for n in self.nodes:
            if n.is_directory:
                self.client.directory.delete_recursive(n.key)
            else:
                self.client.node.delete(n.key)

        self.nodes = []
        self.client = None 

    def random_key(self, basename='key'):
        return '{}{}'.format(basename, random.randint(1, 100000))

    def random_node(self, value=0, ttl=None):
        k = self.random_key('/testnode')
        args = {
            'path': k,
            'value': value
        }
        if ttl:
            args['ttl'] = ttl

        node = self.client.node.create_only(**args)
        self.nodes.append(node)
        assert(not node.is_directory)
        return node 

    def random_dir(self, base='/'):
        k = self.random_key('{}testdir_{}'.format(base, random.randint(1, 100000)))
        node = self.client.directory.create(k)
        assert(node.is_directory)
        self.nodes.append(node)
        return node 

#           ssl_ca_bundle_filepath='/home/dustin/development/python/etcd/tests/ssl/rootCA.pem')
#c = Client()

#ssl_root = '/home/dustin/development/python/etcd/tests/ssl'

#c = Client(host='127.0.0.1', port=2379) 
#           is_ssl=True, 
#           ssl_ca_bundle_filepath=join(ssl_root, 'demoCA', 'cacert.pem'),
#           ssl_client_cert_filepath=join(ssl_root, 'client.crt'), 
#           ssl_client_key_filepath=join(ssl_root, 'client.key'),
#           ssl_client_cert_filepath='/home/dustin/development/python/etcd/tests/ssl/cert_2_newca/alien_client.crt', 
#           ssl_client_key_filepath='/home/dustin/development/python/etcd/tests/ssl/cert_2_newca/alien_client.key')
#)


