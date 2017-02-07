#!/usr/bin/python

import sys
import unittest
import os
import inspect
import re

from optparse import OptionParser

#
# Fix up import path if running directly
#
if __name__ == '__main__':
    filename = os.path.abspath(inspect.getfile(inspect.currentframe()))
    thispath = os.path.dirname(filename)
    normpath = os.path.normpath(os.path.join(thispath, os.pardir))
    sys.path.insert(0, normpath)

import etcd

import test_system
import test_node
import test_directory

def setup_requests_logging(verbose):
    import requests
    import logging

    log_level = logging.INFO
    if verbose:
        log_level = logging.DEBUG

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
    logging.basicConfig()
    logging.getLogger().setLevel(log_level)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(log_level)
    requests_log.propagate = True


def run():
    parser = OptionParser()
    parser.add_option('-l', '--list', dest='list', action='store_true',
        help='List all test cases')
    parser.add_option('-r', '--requests', dest='requests', action='store_true',
        help='Enable logging of requests')
    parser.add_option('-v', '--verbose', dest='verbose', action='store_true',
        help='Enable verbose logging')
    parser.add_option('-f', '--filter', dest='filter', type='string', action='store',
        help='Filter test cases with a regular expression')
    options, args = parser.parse_args()

    all_tests = [
        test_system.suite(),
        test_node.suite(),
        test_directory.suite(),
    ]

    if options.list:
        for suite in all_tests:
            for t in suite:
                print t.id()
        return

    if options.filter:
        pattern = re.compile(options.filter)
        def expand_tests():
            for suite in all_tests:
                for t in suite:
                    yield t
             
        def pattern_match(test):
            name = test.id()
            return pattern.match(name) is not None
        all_tests = unittest.TestSuite(filter(pattern_match, expand_tests()))
    else:
        all_tests = unittest.TestSuite(all_tests)

    test_verbosity = 1 
    if options.verbose:
        test_verbosity = 3

    if options.requests:
        setup_requests_logging(options.verbose)

    unittest.TextTestRunner(verbosity=test_verbosity, failfast=True).run(all_tests)

if __name__ == '__main__':
    run()

