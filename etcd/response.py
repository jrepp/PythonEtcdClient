import simplejson
import logging

import dateutil.parser
import requests

import etcd.exceptions

from collections import namedtuple
from os.path import basename
from datetime import datetime, timedelta


_logger = logging.getLogger(__name__)


A_DELETE = 'delete'
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
        # print('_process_ttl {}'.format(expiration))
        ttl = json['ttl'],
        expiration = dateutil.parser.parse(expiration)
    return (ttl, expiration)


class Node(object):
    def __init__(self):
        self.key = None
        self.json = None
        self.is_error = False
        self.is_deleted = False
        self._children = None
    
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
            return self.from_error(response.status_code, json)

        if 'action' in json:
            self.is_deleted = json['action'] in (A_DELETE, A_CAD)

        return self.from_node_json(json['node'])

    def from_node_json(self, json):
        if json is None:
            self.set_defaults()
            return self

        self.json = json

        if json.get('dir', False):
            self._children = json.get('nodes', [])
        else:
            self._children = None

        self.created_index = json['createdIndex']
        self.modified_index = json['modifiedIndex']
        self.key = json['key']

        # >> Process TTL-related properties. 
        self.ttl, self.expiration = _process_ttl(json)
        
        # Alive nodes will contain values
        self.value = json.get('value')

        self.prev = Node().from_node_json(json.get('prevNode'))

        return self


    def from_error(self, status_code, json):        
        # Translate response code
        self.is_deleted = status_code == requests.status_codes.codes.not_found

        # Capture error metadata
        self.is_error = True
        self.error_code = json['errorCode']
        self.error_message = json['message']
        self.key = json['cause']
        self.index = json['index']
        self.set_defaults()
        return self

    def set_defaults(self):
        self.created_index = None
        self.modified_index = None
        self.prev = None
        self._children = None
        self.ttl = None
        self.expiration = None
        self.value = None

    @property     
    def children(self):
        def _from_node_json(json):
            return Node().from_node_json(json)
        if not self._children:
            return []
        elif type(self._children[0]) is dict:
            self._children = map(_from_node_json, self._children)
        return self._children
    
    @property
    def is_directory(self):
        return self._children is not None
    
    @property
    def is_hidden(self):
        return self.key and self.key[0] == '_'

    def __repr__(self):
        node_count_phrase = (len(self._children) if self._children else '<NA>')
        error_phrase = ('{} ({})'.format(self.error_message, self.error_code) if self.is_error else '<NA>')
        ttl_phrase = '{}: {}'.format(self.ttl, self.expiration)
        return '<NODE({}) ERROR=[{}] IS_HID=[{}] IS_DEL=[{}] IS_DIR=[{}] ' \
                    'COUNT=[{}] TTL=[{}] CI=({}) MI=({})>'.format(
                    self.key, error_phrase,
                    self.is_hidden, self.is_deleted, self.is_directory, 
                    node_count_phrase, ttl_phrase, self.created_index, 
                    self.modified_index)

