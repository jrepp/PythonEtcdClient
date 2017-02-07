import unittest

import common

class SystemTestCase(common.TestCase):
    def test_stats(self):            
        s = self.client.stat.get_leader_stats()
        self.assertIsNotNone(s)

        s = self.client.stat.get_self_stats()
        self.assertIsNotNone(s)

    def test_server_version(self):
        version = self.client.server.get_version()
        self.assertTrue(len(version) > 0)
        self.assertIsInstance(version, unicode)
    
    def _test_server_get_leader_url_prefix(self):
        # Disabled for 404 Client Error: Not Found for url: http://127.0.0.1:2379/v2/leader
        print(self.client.server.get_leader_url_prefix())

    def _test_server_get_machines(self):
        # Disabled for generator error
        for machine in self.client.server.get_machines().children:
            print(machine.value)

    def test_server_get_dashboard_url(self):
        url = self.client.server.get_dashboard_url()
        self.assertTrue(len(url) > 0)
        self.assertIsInstance(url, str)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(SystemTestCase)
   
