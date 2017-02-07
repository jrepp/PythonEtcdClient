import requests
import simplejson

from etcd.common_ops import CommonOps
from etcd.response import Node 
from etcd.compat import parse_qsl


class ServerOps(CommonOps):
    """Functions that query the server for cluster-level information."""

    def get_version(self):
        """Return a string representing the version of the server that we're 
        connected to.

        :returns: Version
        :rtype: string
        """

        version_string = self.get_text('version', '/version', version=None)

        # Version should look like "etcd v0.2.0".
        prefix = 'etcd v'

        if version_string.startswith(prefix):
            return version_string[len(prefix):]
        elif version_string.startswith('{'):
            version_doc = simplejson.loads(version_string)
            version_property = version_doc.get('etcdserver')
            if not version_property: 
                raise ValueError("Invalid version response: %s" % (version_string))
            return version_property
        else:
            raise ValueError("Could not parse server version from: %s" % (version_string))
        

    def get_leader_url_prefix(self):
        """Return the URL prefix of the leader host.

        :returns: URL prefix
        :rtype: string
        """

        return self.get_text('leader', '/leader')

    def get_machines(self):
        """Return the list of servers in the cluster represented as nodes.

        :returns: Node object
        :rtype: :class:`etcd.response.Node`
        """

        fq_path = self.get_fq_node_path('/_etcd/machines')
        response = self.client.send(2, 'get', fq_path, allow_reconnect=False)

        for machine in response.node.children:
            yield parse_qsl(machine.value)

    def get_members(self):
        response = self.client.send(2, 'get', '/members', allow_reconnect=True, return_raw=True)
        members_doc = simplejson.loads(response.content)
        return members_doc.get('members')


    def get_dashboard_url(self):
        """Return the URL for the dashboard on the server currently connected-
        to.

        :returns: URL
        :rtype: string
        """

        return (self.client.prefix + '/mod/dashboard')

