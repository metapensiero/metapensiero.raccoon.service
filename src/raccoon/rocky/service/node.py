# -*- coding: utf-8 -*-
# :Project: raccoon.rocky.service -- base node
# :Created: ven 23 dic 2016 14:13:55 CET
# :Author:  Alberto Berti <alberto@metapensiero.it>
# :License: GNU General Public License version 3 or later
#

from raccoon.rocky.node import call
from raccoon.rocky import node


class ServiceNode:
    """Base node for all the service stuff."""

    node_location = None
    """The location record"""

    on_node_primary_signal = Signal()
    """Signal used to receive 'infrastructure' messages. The messages that
    implement the pairing protocol are of type 'pairing_request', 'peer_ready'
    and 'peer_start'.
    """
    on_node_primary_signal.name = '.'

    def node_bind(self, path, context=None, parent=None):
        from . import system
        result = super().node_bind(path, context, parent)
        self.node_location = system.register_node(self)
        return result

    def node_depend(self):
        self.node_location.depend()

    @call
    def node_info(self, **_):
        from . import system
        return {
            'uri': str(self.node_path),
            'type': self.__class__.__name__,
            'system': system.node_info()
        }

    def node_resolve(self, uri):
        from . import system
        if isinstance(uri, node.Path):
            uri = str(uri)
        else:
            uri = str(self.node_path.resolve(uri, self.node_context))
        return system.resolve(uri)

    def node_unbind(self):
        from . import system
        result = super().node_unbind()
        system.unregister_node(self)
        return result


class Node(ServiceNode, node.Node):
    pass


class WAMPNode(ServiceNode, node.WAMPNode):
    pass
