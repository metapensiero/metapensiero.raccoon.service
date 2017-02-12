# -*- coding: utf-8 -*-
# :Project:   raccoon.rocky.service -- base node
# :Created:   ven 23 dic 2016 14:13:55 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016, 2017 Arstecnica s.r.l.
#

from abc import ABCMeta
import reprlib

from metapensiero.reactive import get_tracker, ReactiveDict, ReactiveChainMap
from metapensiero.signal import Signal, SignalAndHandlerInitMeta
from raccoon.rocky.node import call
from raccoon.rocky.node.wamp import WAMPInitMeta
from raccoon.rocky import node

class ABCSignalHandlerMeta(ABCMeta, SignalAndHandlerInitMeta):
    pass

class ABCWAMPMeta(ABCSignalHandlerMeta, WAMPInitMeta):
    pass

class ServiceNode(metaclass=SignalAndHandlerInitMeta):
    """Base node for all the service stuff."""

    node_location = None
    """The location record."""

    on_node_primary_signal = Signal()
    """Signal used to receive *infrastructure* messages. The messages that
    implement the pairing protocol are of type 'pairing_request', 'peer_ready'
    and 'peer_start'.
    """

    on_node_primary_signal.name = '.'

    def _is_serializable(self, value):
        return (value is None or value is True or value is False or
                isinstance(value, (list, tuple, dict, int, float, str)))

    def _node_children(self):
        return {k:v for k, v in self.__dict__.items()
                if k != 'node_parent' and isinstance(v, node.Node)}

    def _node_description(self):
        desc = {}
        res = {
            'info': self.node_info(),
            'description': desc
        }
        if self.node_context:
            for k, v in self.node_context.items():
                if k not in self.node_context.CONFIG_KEYS and \
                   self._is_serializable(v):
                    desc[k] = v
        return res

    async def _node_unbind(self):
        from . import system
        await super()._node_unbind()
        system.unregister_node(self)

    async def _node_bind(self, path, context=None, parent=None):
        from . import system
        await super()._node_bind(path, context, parent)
        self.node_location = system.register_node(self)

    async def node_add(self, name, value):
        await super().node_add(name, value)
        self.__setitem__(name, value)

    def node_changed(self):
        self.node_location.changed()

    def node_depend(self):
        self.node_location.depend()

    def node_info(self):
        from . import system
        return {
            'uri': str(self.node_path),
            'type': self.__class__.__name__,
            'system': system.node_info()
        }

    def node_primary_description(self, span=0):
        res = {
            '.': self._node_description()
        }
        if span > 0:
            for name, node_ in self._node_children().items():
                if isinstance(node_, ServiceNode):
                    res[name] = node_.node_primary_description(span=span-1)
                else:
                    res[name] = None
        return res

    async def node_remove(self, name):
        self.__delitem__(name)
        await super().node_remove(name)

    def node_resolve(self, uri):
        from . import system
        if isinstance(uri, node.Path):
            uri = str(uri)
        else:
            uri = str(self.node_path.resolve(uri, self.node_context))
        return system.resolve(uri)


class ReactiveServiceNode(ReactiveDict, ServiceNode,
                          metaclass=ABCSignalHandlerMeta):
    """A Node that is also a mapping, accessible via the
    `collections.abc.MutableMapping` protocol. Every value stored gets its own
    dependency so it can be tracked independently. any new node added via
    `node_add` becomes part of this tracking. It exposes four different
    streams of changes to it:

    `structure`
      tracks all the `__setitem__` of new keys and the `__delitem__`.

    `immutables`
      tracks all the changes to keys with hashable values.

    `reactives`
      track the changes to the values that are reactive (like other nodes).

    `all`
      an union of the previous three
    """

    __hash__ = ServiceNode.__hash__
    __eq__ = ServiceNode.__eq__

    def __repr__(self):
        return "<%s  at '%s', %r>" % (self.__class__.__name__,
                                      self.node_path, self.data)


class ReactiveContextNode(ReactiveChainMap, ServiceNode,
                          metaclass=ABCSignalHandlerMeta):
    """A context-manager Node. It's similar to the `ReactiveServiceNode` but
    exposes a global context in the `globals` member. Its own reactive storage
    is mapped as a layer on this one.

    :param \*maps: a list of mappings that will form the new global context.
      If not given, it will be initialized to an empty one.
    """

    __hash__ = ServiceNode.__hash__
    __eq__ = ServiceNode.__eq__

    globals = None
    """A `ReactiveChainMap` containing the global context."""

    def __init__(self, *maps):
        self.globals = ReactiveChainMap(*maps)
        ReactiveChainMap.__init__(self, {}, *self.globals.maps)

    @reprlib.recursive_repr()
    def __repr__(self):
        return "<%s  at '%s', %s>" % (self.__class__.__name__,
                                      self.node_path,
                                      ', '.join(map(repr, self.maps)))

    def new_context(self, local=False, **kwargs):
        if local:
            res = (kwargs,) + tuple(self.maps)
        else:
            res = (kwargs, ) + tuple(self.globals.maps)
        return res

class Node(ReactiveServiceNode, node.Node):
    """A mix between a :class:`ServiceNode` and a
    :class:`~raccoon.rocky.node.node.Node`.
    """


class WAMPNode(ReactiveServiceNode, node.WAMPNode, metaclass=ABCWAMPMeta):
    """A mix between a :class:`ServiceNode` and a
    :class:`~raccoon.rocky.node.node.WAMPNode`.
    """

    @call
    def node_info(self):
        return super().node_info()

    @call('.')
    def node_primary_description(self, span=0):
        return super().node_primary_description(span)



class ContextNode(ReactiveContextNode, node.WAMPNode, metaclass=ABCWAMPMeta):

    @call
    def node_info(self):
        return super().node_info()

    @call('.')
    def node_primary_description(self, span=0):
        return super().node_primary_description(span)


def when_node(condition, *nodes):
    """
    Return a computation that will evaluate a `condition` on one or more
    `nodes` and that will be automatically re-executed when one of the nodes
    is marked as changed.
    """

    def eval_condition(computation):
        for n in nodes:
            n.node_depend()
        return condition(*nodes)

    return get_tracker().async_reactive(eval_condition, initial_value=False)
