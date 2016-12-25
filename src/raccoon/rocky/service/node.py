# -*- coding: utf-8 -*-
# :Project: raccoon.rocky.service -- base node
# :Created: ven 23 dic 2016 14:13:55 CET
# :Author:  Alberto Berti <alberto@metapensiero.it>
# :License: GNU General Public License version 3 or later
#

from raccoon.rocky import node


class ServiceNode:
    """Base node for all the service stuff."""

    node_location = None
    """The location record"""

    def node_bind(self, path, context=None, parent=None):
        from . import system
        result = super().node_bind(path, context, parent)
        self.node_location = system.register_node(self)
        return result

    def node_depend(self):
        self.node_location.depend()

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
