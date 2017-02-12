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


def _from_json(json):
    n = Node()
    n.from_json(json)
    return n


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
    def __init__(self):
        pass
    
    def from_response(self, response, verb, path):
        try:
            json = response.json()
        except simplejson.JSONDecodeError:
            # Bug #1120: Wait will timeout with a JSON-message of zero-length.
            if response.text == '':
                raise etcd.exceptions.EtcdEmptyResponseError()
            else:
                raise

        _logger.debug("Response JSON: {}".format(json))

        if 'errorCode' in json:
            self.process_error(response.status_code, json)
            return

        self.from_json(json)

    def from_json(self, json):
        self.json = json
        self.is_error = False

        action = json.get('action')
        node = json.get('node')

        self._children = []
        self.is_directory = False
        self.is_deleted = False
        self.created_index = node['createdIndex']
        self.modified_index = node['modifiedIndex']
        self.key = node['key']
        self.is_deleted = action in (A_DELETE, A_CAD)

        # This is as involved as we'll get with whether nodes are hidden. Any 
        # more, and we'd have to manage and, therefore, translate every key 
        # reported by the server.
        self.is_hidden = basename(node['key']).startswith('_')

        # >> Process TTL-related properties. 
        self.ttl, self.expiration = _process_ttl(node)
        
        # Alive nodes will contain values
        self.value = node.get('value')

        if node.get('dir'):
            if node.get('dir', False) is True:
                self.is_directory = True
                self._children = node.get('nodes', [])

        self.action = action
        self.node = node

        prev = json.get('prevNode')
        if prev is not None:
            self.prev_node = build(prev)


    def process_error(self, status_code, json):        
        # Translate response code
        self.is_deleted = status_code == requests.status_codes.codes.not_found

        # Capture error metadata
        self.is_error = True
        self.error_code = json['errorCode']
        self.error_message = json['message']
        self.key = json['cause']
        self.index = json['index']
        
        # Set defaults for node
        self.is_hidden = False
        self.is_directory = False
        self.created_index = None
        self.modified_index = None
        self.prev_node = None
        self._children = None
        self.ttl = None
        self.expiration = None
        self.action = None
        self.value = None
   
    @property     
    def children(self):
        if not self._children:
            return None
        elif type(self._children[0]) is dict:
            self._children = map(_from_json, self._children)


    def __repr__(self):
        node_count_phrase = (len(self._children) if self._children else '<NA>')
        error_phrase = ('{} ({})'.format(self.error_message, self.error_code) if self.is_error else '<NA>')
        ttl_phrase = '{}: {}'.format(self.ttl, self.expiration)
        return '<NODE({}) [{}] ERROR=[{}] IS_HID=[{}] IS_DEL=[{}] IS_DIR=[{}] ' \
                    'COUNT=[{}] TTL=[{}] CI=({}) MI=({})>'.format(
                    self.key, self.action, error_phrase,
                    self.is_hidden, self.is_deleted, self.is_directory, 
                    node_count_phrase, ttl_phrase, self.created_index, 
                    self.modified_index)

    
