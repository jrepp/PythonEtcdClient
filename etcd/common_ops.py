from requests.exceptions import HTTPError, ChunkedEncodingError
from requests.status_codes import codes

from etcd.exceptions import EtcdPreconditionException, EtcdEmptyResponseError,\
                            EtcdWaitFaultException


class CommonOps(object):
    """Base-class of 'ops' modules.

    :param client: Client instance.
    :type client: :class:`etcd.client.Client`
    """

    def __init__(self, client):
        self.__client = client

    def get_text(self, reason, path, version=2):
        """Execute a request that will return flat text.

        :param reason: Brief phrase describing the request
        :param path: URL path
        :param version: API version

        :type reason: string
        :type path: string
        :type version: int

        :returns: Response text
        :rtype: string
        """

        if version is not None:
            url = ('%s/v%d%s' % (self.client.prefix, version, path))
        else:
            url = ('%s%s' % (self.client.prefix, path))

        self.client.debug("TEXT URL (%s) = [%s]" % (reason, url))

        r = self.client.session.get(url)
        r.raise_for_status()

        return r.text

    def validate_path(self, path):
        """Validate the key that we were given.

        :param path: Key
        :type path: string

        :raises: ValueError
        """

        if path[0] != '/':
            raise ValueError("Path [%s] should've been absolute." % (path,))

    def get_fq_node_path(self, path):
        """Return the full path of the given key.

        :param path: Key
        :type path: string
        """

        self.validate_path(path)

        return ('/keys' + path)

    def compare_and_delete(self, path, is_dir, current_value=None, 
                           current_index=None, is_recursive=None):
        """The base compare-and-delete function for atomic deletes. A  
        combination of criteria may be used if necessary.
        
        :param path: Key
        :type path: string

        :param is_dir: If the node is a directory
        :type is_dir: bool

        :param current_value: Current value to check
        :type current_value: string or None

        :param current_index: Current index to check
        :type current_index: int or None

        :returns: Node object
        :rtype: :class:`etcd.response.Node`
        """

        fq_path = self.get_fq_node_path(path)

        parameters = {}

        if current_value is not None:
            parameters['prevValue'] = current_value
        elif current_index is not None:
            parameters['prevIndex'] = current_index
        else:
            raise ValueError("CAD requires a comparison argument.")

        if is_recursive is not None:
            # Per the discussion, "-r will also imply -d".
            is_dir = True

            if is_recursive is True:
                parameters['recursive'] = 'true'

        parameters['dir'] = 'true' if is_dir is True else 'false'
        
        return self.client.send(2, 'delete', fq_path, parameters=parameters)

        
    def wait(self, path, recursive=False, force_consistent=False):
        """Long-poll on the given path until it changes.

        :param path: Node key
        :type path: string

        :param recursive: Wait on any change in the given directory or any of 
                          its descendants.
        :type recursive: bool

        :returns: Node object
        :rtype: :class:`etcd.response.Node` or None

        :raises: KeyError
        """

        fq_path = self.get_fq_node_path(path)

        parameters = { 'wait': 'true' }

        if recursive is True:
            parameters['recursive'] = 'true'

        if force_consistent is True:
            parameters['consistent'] = 'true'

        try:
            return self.client.send(2, 'get', fq_path, parameters=parameters)
        except ChunkedEncodingError:
# TODO(dustin): We need to document why we would get this. We don't remember 
#               the context.
            pass
        except EtcdEmptyResponseError:
# TODO(dustin): This will happen when we timeout, and should be considered a 
#               bug as it does not constitute valid JSON.
#
#               https://github.com/coreos/etcd/issues/1120
            pass

        raise EtcdWaitFaultException()

    @property
    def client(self):
        return self.__client
