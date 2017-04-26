import random
import logging

import requests
import ssl
import semver

from os import environ
from requests.exceptions import ConnectionError
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
from datetime import datetime

from etcd.config import HOST_FAIL_WAIT_S
from etcd.directory_ops import DirectoryOps
from etcd.node_ops import NodeOps
from etcd.server_ops import ServerOps
from etcd.stat_ops import StatOps
from etcd.modules.lock import LockMod
from etcd.modules.leader import LeaderMod
from etcd.response import Node

logging.getLogger('requests.packages.urllib3').setLevel(logging.WARN)

_VALID_RESPONSE_ERRORS = (
    requests.status_codes.codes.bad_request, 
    requests.status_codes.codes.not_found,
    requests.status_codes.codes.precondition_failed,
    requests.status_codes.codes.forbidden,
)

_logger = logging.getLogger(__name__)

_SSL_DO_VERIFY = bool(int(environ.get('PEC_SSL_DO_VERIFY', '1')))

_SSL_CA_BUNDLE_FILEPATH = environ.get(
                            'PEC_SSL_CA_BUNDLE_FILEPATH', 
                            '') or None
_SSL_CLIENT_CRT_FILEPATH = environ.get(
                            'PEC_SSL_CLIENT_CRT_FILEPATH', 
                            '') or None

_SSL_CLIENT_KEY_FILEPATH = environ.get(
                            'PEC_SSL_CLIENT_KEY_FILEPATH', 
                            '') or None


class _SslHttpAdapter(HTTPAdapter):
    """"Transport adapter" for requests module that creates TLS connections."""

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = PoolManager(num_pools=connections,
                                       maxsize=maxsize,
                                       block=block,
                                       ssl_version=self.best_ssl_version())

    def best_ssl_version(self):
        # Use recommended settings from ssl module docs with fallbacks to
        # earlier module definitions
        # https://docs.python.org/2/library/ssl.html#ssl.PROTOCOL_TLS
        versions = ['PROTOCOL_TLS', 'PROTOCOL_SSLv3', 'PROTOCOL_SSLv23']
        for v in versions:
            if v in ssl.__dict__:
                return ssl.__dict__[v]
        raise ValueError('Supported SSL protocol not found')


class _Modules(object):
    """Intermediate container that holds functionality related to modules.

    :param client: Client instance
    :type client: :class:`etcd.client.Client`
    """

    def __init__(self, client):
        self.__client = client

    @property
    def lock(self):
        """Return an instance of the class having the lock functionality.

        :rtype: :class:`etcd.response.Node`
        """

        try:
            return self.__lock
        except AttributeError:
            self.__lock = LockMod(self.__client)
            return self.__lock

    @property
    def leader(self):
        """Return an instance of the class having the leader-election 
        functionality.

        :rtype: :class:`etcd.modules.leader.LeaderMod`
        """

        try:
            return self.__leader
        except AttributeError:
            self.__leader = LeaderMod(self.__client)
            return self.__leader


class Client(object):
    """The main channel of functionality for the client. Connects to the 
    server, and provides functions via properties.

    :param host: Hostname or IP of server
    :type host: string

    :param port: Port of server
    :type port: int

    :param is_ssl: Whether to use 'http://' or 'https://'.
    :type is_ssl: bool

    :param ssl_do_verify: Whether to verify the certificate hostname.
    :type ssl_do_verify: bool or None

    :param ssl_ca_bundle_filepath: A bundle of rootCAs for verifications.
    :type ssl_ca_bundle_filepath: string or None

    :param ssl_client_cert_filepath: A client certificate, for authentication.
    :type ssl_client_cert_filepath: string or None

    :param ssl_client_key_filepath: A client key, for authentication.
    :type ssl_client_key_filepath: string or None

    :raises: ValueError
    """

    def __init__(self,
                 host='127.0.0.1',
                 port=4001,
                 is_ssl=False, ssl_do_verify=_SSL_DO_VERIFY, 
                 ssl_ca_bundle_filepath=_SSL_CA_BUNDLE_FILEPATH, 
                 ssl_client_cert_filepath=_SSL_CLIENT_CRT_FILEPATH, 
                 ssl_client_key_filepath=_SSL_CLIENT_KEY_FILEPATH):

        if ssl_do_verify is not None:
            _logger.debug("SSL: Explicit verify setting given: [%s]", ssl_do_verify)
            self.__ssl_verify = ssl_do_verify

        elif ssl_ca_bundle_filepath is not None:
            _logger.debug("SSL: We'll be verifying against a CA bundle: [%s]", 
                          ssl_ca_bundle_filepath)

            self.__ssl_verify = ssl_ca_bundle_filepath

        else:
            _logger.debug("SSL: We'll verify the CA certificate, by default.")

            self.__ssl_verify = True

        if ssl_client_cert_filepath is None:
            _logger.debug("SSL: No client key/certificate will be used.")
            self.__ssl_cert = None

        elif ssl_client_key_filepath is not None:
            _logger.debug("SSL: Client key and certificate will be used: "
                          "KEY=[%s] CERTIFICATE=[%s]",
                          ssl_client_key_filepath, ssl_client_cert_filepath)

            self.__ssl_cert = \
                (ssl_client_cert_filepath, 
                 ssl_client_key_filepath)

        else:
            _logger.debug("SSL: Client certificate will be used (without a "
                          "key): [%s]", ssl_client_cert_filepath)

            self.__ssl_cert = ssl_client_cert_filepath

        scheme = 'http' if is_ssl is False else 'https'
        self.__prefix = ('%s://%s:%s' % (scheme, host, port))
        _logger.debug("PREFIX= [%s]", self.__prefix)

        self.__session = requests.Session()

        # Define an adapter for when SSL is requested.
        self.__session.mount('https://', _SslHttpAdapter())

        self.init_version()

        # TODO: determine when machines tree went away for version check
        if semver.match(self.__version, '<3.0.0'):
            self.__machines = [[dict(machine_info)['etcd'], None]
                for machine_info in self.server.get_machines()]
        else:
            self.__machines = [[member['clientURLs'][0], None] 
                for member in self.server.get_members()]

        _logger.debug("Cluster machines: %s", self.__machines)

        self.__machine_index = None
        self.cycle_machine_index()
        
        _logger.debug("The initial machine is at index (%d).",
                      self.__machine_index)

    def __str__(self):
        return ('<ETCD %s>' % (self.__prefix))

    def debug(self, msg):
        _logger.debug(msg)
    
    def init_version(self):
        self.__version = self.server.get_version()
        self.debug("ETCD Version: %s" % (self.__version))

        if not semver.match(self.__version, '>=0.2.0'):
            raise ValueError("We don't support an etcd version older than 0.2.0 .")

    def cycle_machine_index_on_failure(self):
        """
        Mark the current member failed, find the next alive machine
        """
        now_dt = datetime.now()
        self.__machines[self.__machine_index][1] = now_dt

        c = len(self.__machines)
        i = 0
        elected = None
        while i < c:
            machine_index = (self.__machine_index + 1) % c
            (prefix, last_fail_dt) = self.__machines[machine_index]

            if last_fail_dt is None or \
               (now_dt - last_fail_dt).total_seconds() > \
                    HOST_FAIL_WAIT_S:
                elected = prefix

            i += 1

        if elected is None:
            raise SystemError("All servers have failed: %s" % 
                              (self.__machines,))

        self.__prefix = elected
        self.__machine_index = machine_index

        _logger.debug("Retrying with next machine: %s", self.__prefix)

    def cycle_machine_index(self):
        """
        Randomly select a new member of the cluster for communication
        """
        if len(self.__machines) == 0:
            return
        # Always rotate to a uniformly random instance to avoid hitting 
        # the same node in all clients
        self.__machine_index = random.randint(0, len(self.__machines) - 1)

    def send(self, version, verb, path, value=None, parameters=None, data=None, 
             module=None, return_raw=False, allow_reconnect=True):
        """Build and execute a request.

        :param version: Version of API
        :type version: int

        :param verb: Verb of request ('get', 'post', etc..)
        :type verb: string

        :param path: URL path
        :type path: string

        :param value: Value to be converted to string and passed as "value" in 
                      the POST data.
        :type value: scalar or None

        :param parameters: Dictionary of values to be passed via URL query.
        :type parameters: dictionary or None

        :param data: Dictionary of values to be passed via POST data.
        :type data: dictionary or None

        :param module: Name of the etcd module that hosts the functionality.
        :type module: string or None

        :param return_raw: Whether to return a 
                           :class:`etcd.response.Node` object or the raw 
                           Requests response.
        :type return_raw: bool

        :param allow_reconnect: Allow the client to consider alternate hosts if
                                the current host fails connection.
        :type allow_reconnect: bool

        :returns: Node object
        :rtype: :class:`etcd.response.Node`
        """

        if parameters is None:
            parameters = {}

        if data is None:
            data = {}

        if version != 2:
            raise ValueError("Version ({0}) request is not supported.".format(version))

        if module is None:
            url = ('%s/v%d%s' % (self.__prefix, version, path))
        else:
            url = ('%s/mod/v%d/%s%s' % (self.__prefix, version, module, path))

        if value is not None:
            data['value'] = value

        args = { 'params': parameters, 
                 'data': data, 
                 'verify': self.__ssl_verify, 
                 'cert': self.__ssl_cert }

        _logger.debug("Request(%s)=[%s] params=[%s] data_keys=[%s]",
                      verb, url, parameters, args['data'].keys())

        send = getattr(self.__session, verb)
    
        while 1:
            try:
                r = send(url, **args)
            except ConnectionError as e:
                _logger.debug("Connection error with [%s] [%s]: %s",
                              self.__prefix, e.__class__.__name__, str(e))

                if allow_reconnect is False:
                    raise
            else:
                break

            # If we get here, there was a connection problem. Rotate the server 
            # that we're using, excluding any that have recently failed.
            self.cycle_machine_index_on_failure()

            
        # Pass back the requests library response object
        if return_raw is True:
            return r

        # For unhandled status codes allow requests to raise 
        if r.status_code not in _VALID_RESPONSE_ERRORS:
            r.raise_for_status()

        # Everything else is a Node (existent or otherwise)
        return Node().from_response(r, verb, path)

    @property
    def session(self):
        return self.__session

    @property
    def prefix(self):
        """Return the URL prefix for the server.

        :rtype: string
        """

        return self.__prefix

    @property
    def directory(self):
        """Return an instance of the class having the directory functionality.

        :rtype: :class:`etcd.directory_ops.DirectoryOps`
        """

        try:
            return self.__directory
        except AttributeError:
            self.__directory = DirectoryOps(self)
            return self.__directory

    @property
    def node(self):
        """Return an instance of the class having the general node 
        functionality.

        :rtype: :class:`etcd.node_ops.NodeOps`
        """

        try:
            return self.__node
        except AttributeError:
            self.__node = NodeOps(self)
            return self.__node

    @property
    def server(self):
        """Return an instance of the class having the server functionality.

        :rtype: :class:`etcd.server_ops.ServerOps`
        """

        try:
            return self.__server
        except AttributeError:
            self.__server = ServerOps(self)
            return self.__server

    @property
    def stat(self):
        """Return an instance of the class having the stat functionality.

        :rtype: :class:`etcd.stat_ops.StatOps`
        """

        try:
            return self.__stat
        except AttributeError:
            self.__stat = StatOps(self)
            return self.__stat

    @property
    def module(self):
        """Return an instance of the class that hosts the functionality 
        provided by individual modules.

        :rtype: :class:`etcd.client._Modules`
        """

        try:
            return self.__module
        except AttributeError:
            self.__module = _Modules(self)
            return self.__module
