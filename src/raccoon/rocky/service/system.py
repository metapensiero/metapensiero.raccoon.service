# -*- coding: utf-8 -*-
# :Project:   arstecnica.ytefas.appserver -- system meta object
# :Created:   gio 22 dic 2016 15:00:38 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016, 2017 Arstecnica s.r.l.
#

import sys
import weakref

from metapensiero.reactive import get_tracker
from raccoon.rocky.node import Path
from .node import Node


class SystemError(Exception):
    """Error raised during system operations."""


class System(Node):

    NODE_LOCATION = {}
    LOCATION_NODE = {}
    URI_NODE = {}

    name = 'server'

    def node_info(self):
        return {
            'name': self.name,
            'lang': 'Python'
        }

    def register_node(self, node):
        assert hasattr(node, 'node_path') and \
            isinstance(node.node_path, Path) and \
            node not in self.NODE_LOCATION
        loc = Location(node)
        self.NODE_LOCATION[node] = loc
        self.LOCATION_NODE[loc] = node
        self.URI_NODE[str(loc.key)] = node
        return loc

    def resolve(self, uri):
        return self.URI_NODE.get(uri)

    def unregister_node(self, node):
        loc = self.NODE_LOCATION[node]
        del self.NODE_LOCATION[node]
        del self.LOCATION_NODE[loc]
        del self.URI_NODE[str(loc.key)]


system = System()


class LocationMeta(type):

    def __call__(self, node):
        if node in system.NODE_LOCATION:
            result = system.NODE_LOCATION[node]
        else:
            result = super().__call__(node)
        return result


class Location(metaclass=LocationMeta):

    def __init__(self, node):
        self._active = True
        self._key = node.node_path.absolute
        self._node = weakref.ref(node)
        self._is_root = node.node_parent is None
        self._dependency = get_tracker().dependency(self)
        node.on_node_unbind.connect(self._on_node_unbind)

    def __hash__(self):
        return hash(self._key)

    def _on_node_unbind(self, node, path, parent):
        assert path.absolute is self._key, "Node changed path after bind"
        self._active = False
        self.changed(override=True)

    def changed(self, override=False):
        if self._active or override:
            self._dependency.changed()
        else:
            raise SystemError("Location no more active")

    def depend(self):
        if self._active:
            self._dependency.depend()
        else:
            raise SystemError("Location no more active")

    @property
    def key(self):
        return self._key

    path = key

    @property
    def is_root(self):
        return self._is_root

    @property
    def node(self):
        return self._node()


sys.modules[__name__] = system
