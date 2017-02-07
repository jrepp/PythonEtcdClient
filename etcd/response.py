import simplejson
import logging

import dateutil.parser
import requests

import etcd.exceptions

from collections import namedtuple
from os.path import basename
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)

A__PREVNODE = '_(pnode)'

A_GET = 'get'
A_SET = 'set'
A_UPDATE = 'update'
A_CREATE = 'create'
A_DELETE = 'delete'
A_CAS = 'compareAndSwap'
A_CAD = 'compareAndDelete'

def _process_ttl(json):
    """
    Parse and convert a node TTL from the JSON document
    """
    try:
        expiration = json['expiration']
    except KeyError:
        ttl = None
        expiration = None
    else:
        # print '_process_ttl {}'.format(expiration)
        ttl = json['ttl'],
        expiration = dateutil.parser.parse(expiration)
    return (ttl, expiration)


class Node(object):
    """Represent all nodes: deleted, alive, missing or collection.

    :param action: Action type
    :param node: Node dictionary

    :type action: string
    :type node: dictionary

    :returns: Node object
    :rtype: etcd.response.Node
    """

    def __init__(self, response, verb, path):
        try:
            json = response.json()
        except simplejson.JSONDecodeError:
            # Bug #1120: Wait will timeout with a JSON-message of zero-length.
            if response.text == '':
                raise etcd.exceptions.EtcdEmptyResponseError()
            else:
                raise

        _logger.debug("Response JSON: {}".format(json))
        self.json = json

        if 'errorCode' in json:
            self.is_deleted = response.status_code == requests.status_codes.codes.not_found
            self.is_error = True
            self.is_hidden = False
            self.is_directory = False
            self.is_collection = False
            self.error_code = json['errorCode']
            self.error_message = json['message']
            self.key = json['cause']
            self.index = json['index']
            self.created_index = None
            self.modified_index = None
            self.prev_node = None
            self.children = None
            self.ttl = None
            self.expiration = None
            self.action = None
            return
        else:
            self.is_error = False

        self.prev_node = json.get('prevNode')

        action = json.get('action')
        node = json.get('node') 

        self.children = []
        self.is_directory = False
        self.is_collection = False
        self.is_deleted = False
        self.created_index = node['createdIndex']
        self.modified_index = node['modifiedIndex']
        self.key = node['key']
        self.is_deleted = action in (A_DELETE, A_CAD)

        # This is as involved as we'll get with whether nodes are hidden. Any 
        # more, and we'd have to manage and, therefore, translate every key 
        # reported by the server.
        self.is_hidden = basename(node['key']).startswith('_')

        # >> Process TTL-related stuff. 
        self.ttl, self.expiration = _process_ttl(node)
        
        # Alive value nodes will contain values
        self.value = node.get('value')

        if node.get('dir'):
            if node.get('dir', False) is True:
                self.is_collection = True
                self.children = node.get('nodes', [])
            else:
                self.is_collection = False

        self.action = action
        self.node = node

    def __repr__(self):
        node_count_phrase = (len(self.children) if self.children else '<NA>')
        error_phrase = ('{} ({})'.format(self.error_message, self.error_code) if self.is_error else '<NA>')
        ttl_phrase = '{}: {}'.format(self.ttl, self.expiration)
        return '<NODE({}) [{}] ERROR=[{}] IS_HID=[{}] IS_DEL=[{}] IS_DIR=[{}] ' \
                    'IS_COLL=[{}] COUNT=[{}] TTL=[{}] CI=({}) MI=({})>'.format(
                    self.key, self.action, error_phrase,
                    self.is_hidden, self.is_deleted, self.is_directory, 
                    self.is_collection, node_count_phrase, ttl_phrase, self.created_index, 
                    self.modified_index)

    
