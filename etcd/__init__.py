__version__ = '2.0.8'

from client import Client

class Context(object):
    def __init__(self, client_conn=None, cwd='/'):
        self.client = client_conn
        self.cwd = cwd

CTX = Context()


def enable_logging():
    """
    Enable logging for the requests library, useful for diagnosing 
    protocol issues at the API level.
    """
    import requests
    import logging
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
    logging.getLogger().setLevel(logging.DEBUG)

    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def translate_path(path):
    """
    Use the global context to fix relative paths within the current
    working directory
    """
    global CTX
    if path is None:
        return CTX.cwd
    if path.startswith('/'):
        return path
    return '{}/{}'.format(CTX.cwd, path)


def connect(**kwargs):
    """
    Set the global context using arguments for a standard client connection.
    """
    global CTX
    CTX = Context(Client(kwargs))


def use(client_conn=None, cwd='/'):
    """
    Set the global context using a pre-existing client and current working directory.
    """
    global CTX
    if client_conn is None:
        client_conn = Client()
    assert(isinstance(client_conn, Client))
    CTX = Context(client_conn, cwd)


def cwd():
    """
    Get the current working directory.
    """
    assert(CTX is not None)
    return CTX.cwd


def node():
    """
    Get a reference to the node of the current working directory.
    """
    assert(CTX is not None)
    n = CTX.client.node.get(CTX.cwd)
    return n


def ls(path=None):
    """
    Get a summary listing of the current working directora or the specified path
    """
    assert(CTX is not None)

    d = CTX.client.directory.list(translate_path(path), sorted=True)
    print(d.json)
    def dir_entry(n):
        if n.is_directory:
            return '{}/'.format(n.key.split('/')[-1])
        elif n.is_error:
            return 'ERROR: {}'.format(n.error_message)
        else:
            return '{}={}'.format(n.key.split('/')[-1], n.value)

    return map(dir_entry, d.children)


def cd(path):
    """
    Change the current working directory
    """
    global CTX
    assert(CTX is not None)

    n = CTX.client.node.get(translate_path(path))

    if n.is_directory:
        CTX.cwd = n.key
        return CTX.cwd
    elif n.is_error:
        raise Exception(n.error_message)
    else:
        raise Exception('{} is not a directory'.format(n))


def mkdir(path):
    """
    Make a new directory at the specified path
    """
    global CTX
    path = translate_path(path)

    n = CTX.client.directory.create(path)
    if n.is_error:
        raise Exception(n.error_message)

    return n.key


def get(path=None):
    """
    Get the value at the specified path
    """
    global CTX
    assert(CTX is not None)
    n = CTX.client.node.get(translate_path(path))
    if n.is_valid:
        return n.value
    elif n.is_deleted:
        raise ValueError('{} was deleted'.format(n))
    else:
        raise Exception(n.error_message)


def set(path, value):
    """
    Set a value at the specified path
    """
    global CTX
    n = CTX.client.node.set(translate_path(path), value)
    if n.is_error:
        raise Exception(n.error_message)
    else:
        return '{}={}'.format(n.key, n.value)


def rm(path):
    """
    Remove a node at the specified path
    """
    global CTX
    if path is None:
        raise ValueError('rm() requires a path argument')
    n = CTX.client.node.delete(translate_path(path))
    if n.is_deleted:
        return '{} deleted'.format(n.key)
    elif n.is_error:
        raise Exception(n.error_message)
    else:
        return '{} rm() failed for unknown reason'.format(n.key)

