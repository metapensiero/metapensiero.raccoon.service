# -*- coding: utf-8 -*-
# :Project:   raccoon.rocky.service -- base node
# :Created:   ven 23 dic 2016 14:13:55 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016, 2017 Arstecnica s.r.l.
#

from metapensiero.reactive import get_tracker
from metapensiero.signal import Signal, SignalAndHandlerInitMeta
from raccoon.rocky.node import call
from raccoon.rocky import node


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
                isinstance(value, (list, tuple, dict, int, float)))

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

    def node_bind(self, path, context=None, parent=None):
        from . import system
        result = super().node_bind(path, context, parent)
        self.node_location = system.register_node(self)
        return result

    def node_depend(self):
        self.node_location.depend()

    def node_info(self, **_):
        from . import system
        return {
            'uri': str(self.node_path),
            'type': self.__class__.__name__,
            'system': system.node_info()
        }

    def node_primary_description(self, span=0, **_):
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

    @call
    def node_info(self, **_):
        return super().node_info()

    @call('.')
    def node_primary_description(self, span=0, **_):
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
