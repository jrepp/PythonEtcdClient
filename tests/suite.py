#!/usr/bin/env python

import sys
import unittest
import os
import inspect
import re
import time
import logging

from optparse import OptionParser

_file_name = os.path.abspath(inspect.getfile(inspect.currentframe()))
_self_path = os.path.dirname(_file_name)
_parent_path = os.path.normpath(os.path.join(_self_path, os.pardir))

#
# Fix up import path if running directly
#
if __name__ == '__main__':
    sys.path.insert(0, _parent_path)

import etcd

import test_system
import test_node
import test_directory

class TestRunner(object):
    def __init__(self, test_verbosity, modules, pattern=None):
        self.test_verbosity = test_verbosity
        self.modules = modules
        self.pattern = pattern
        
    def reload(self):
        self.log.info('reloading {} modules'.format(len(self.modules)))
        self.modules = [reload(m) for m in self.modules]

    def suites(self):
        return [m.suite() for m in self.modules]

    def suite(self):
        return unittest.TestSuite(self.suites())

    def specific_suite(self, suite_name):
        suite = unittest.TestSuite()
        for suite in self.suites():
            for t in suite:
                if t.id().startswith(suite_name):
                    suite.addTest(t)
        return suite

    def filtered_suite(self):
        print('filtering with {}'.format(self.pattern))
        all_suites = self.suites()
        def expand_tests():
            for suite in all_suites:
                for t in suite:
                    yield t
        def pattern_match(test):
            name = test.id()
            return self.pattern.match(name) is not None
        return unittest.TestSuite(filter(pattern_match, expand_tests()))

    def default_suite(self):
        if self.pattern is not None:
            return self.filtered_suite()
        else:
            return self.suite()

    def run(self, suite=None):
        suite = suite or self.default_suite()
        utrunner = unittest.TextTestRunner(verbosity=self.test_verbosity, failfast=True)
        utrunner.run(suite)

    def list(self):            
        def list_r(t):
            if isinstance(t, unittest.TestCase):
                print(t.id())
            if isinstance(t, unittest.TestSuite):
                for child in t:
                    list_r(child)
        list_r(self.default_suite())

#print(dir(self.default_suite()))
#        for suite in self.suites():
#            for t in suite:
#                print(t.id())
#

class TestObserver(object):
    def __init__(self, base_paths, runner):
        """
        Setup a file observer to automatically re-run tests when a python
        file changes.
        """
        self.last_discover = None
        self.last_check = None
        self.file_status = {}
        self.base_paths = base_paths
        self.log = logging.getLogger('testobs')
        self.runner = runner

    def discover(self):
        def each_py(base_path):
            for root, dirs, files in os.walk(base_path):
                for f in files:
                    if f.endswith('.py'):
                        yield os.path.join(root, f)
        def discover_in_path(base_path):
            for f in each_py(base_path):
                self.file_status[f] = os.stat(f).st_mtime
        map(discover_in_path, self.base_paths)
        self.log.info('monitoring {} files for changes'.format(len(self.file_status)))
    
    def poll(self):
        now = time.time()
        if not self.last_discover or self.last_discover > now + 3:
            self.discover()
            self.last_discover = now
        if not self.last_check or self.last_discover > now + 1:
            self.check()


    def check(self):
        # self.log.debug('looking for changes')
        changes = []
        deletes = []
        for f, mtime in self.file_status.iteritems():
            try_count = 0
            # File may just appear gone temporarily while being written
            # if it's still missing, remove it from the file map
            while not os.path.exists(f) and try_count < 3:
                self.log.debug('file does not exist {}'.format(f))
                try_count += 1
                time.sleep(1)
                continue
            if not os.path.exists(f):
               continue

            st_new = os.stat(f)
            if st_new.st_mtime > mtime:
                changes.append((f, st_new.st_mtime,))

        # Process removes and changes
        # self.log.debug('detected {} changes, {} removes'.format(len(changes), len(deletes)))
        
        for f, mtime in deletes:
           self.file_status.pop(f) 
        
        run_all = False
        for f, mtime in changes:
            name = os.path.split(f)
            self.file_status[f] = mtime
            if name[-1].startswith('test_'):
                self.log.info('test suite changed {}'.format(name))
                self.runner.reload()
                self.runner.run(self.runner.specific_suite(f))
            else:
                self.log.info('file changed {}'.format(name))
                run_all = True
         
        if run_all:
            self.runner.reload()
            self.runner.run()


def setup_requests_logging(log_level):
    """
    Enable logging for the requests library, useful for diagnosing 
    protocol issues at the API level.
    """
    import requests
    # These two lines enable debugging at httplib level (requests->urllib3->http.client)
    # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
    # The only thing missing will be the response.body which is not logged.
    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client
        http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(log_level)
    requests_log.propagate = True


def main():
    parser = OptionParser()
    parser.add_option('-l', '--list', dest='list', action='store_true',
        help='List all test cases')
    parser.add_option('-r', '--requests', dest='requests', action='store_true',
        help='Enable logging of requests')
    parser.add_option('-v', '--verbose', dest='verbose', action='store_true',
        help='Enable verbose logging')
    parser.add_option('-f', '--filter', dest='filter', type='string', action='store',
        help='Filter test cases with a regular expression')
    parser.add_option('-a', '--auto', dest='auto', action='store_true',
        help='Run suite in automatic mode, watching for changes')
    options, args = parser.parse_args()
    
    # Configure logging
    test_verbosity = 1 
    if options.verbose:
        test_verbosity = 3
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logging.basicConfig()
    logging.getLogger().setLevel(log_level)

    # Configure logging for the 'requests' library
    if options.requests:
        setup_requests_logging(log_level)

    # Remove tests based on regex filter
    if options.filter:
        pattern = re.compile(options.filter)
    else:
        pattern = None    
    
    # Wrap the test modules with a new runner 
    test_modules = [
        test_system,
        test_node,
        test_directory,
    ]

    runner = TestRunner(test_verbosity, test_modules, pattern)

    # List all tests and exit 
    if options.list:
        runner.list()
        return

    # Execute selected tets

    runner.run()

    # Run auto-testing observer
    if options.auto:
        lib_path = os.path.join(_parent_path, 'etcd')
        test_path = _self_path
        try:
            obs = TestObserver([lib_path, test_path], runner)
            while True:
                obs.poll()
                time.sleep(.2)
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    main()

