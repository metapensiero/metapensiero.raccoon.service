# -*- coding: utf-8 -*-
# :Project:   raccoon.rocky.service -- role path resolver
# :Created:   dom 18 dic 2016 01:59:44 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: © 2016, 2017, 2018 Alberto Berti
#

from collections.abc import Mapping

from raccoon.rocky.node import Node
from raccoon.rocky.node.path import norm_path, PathError
from raccoon.rocky.node.proxy import Proxy


class ContextPathResolver:
    """
    Extend the path resolution machinery with a way to automatically resolve
    peers from their role name.

    This uses a member `peers` which is present on the context after pairing
    completes successfully, defined by :class:`~.node.PairableNode`.
    """

    def __call__(self, path, query, context):
        if not query[0].startswith('#'):
            return
        if len(query) == 1 and query[0] == '#':
            query = ('#context',)
        q = (query[0][1:], *query[1:])
        container = context
        context_path = None
        for ix, name in enumerate(q):
            if name not in container:
                raise PathError("Asked to resolve a nearest '%s' but it's"
                                " not in the node_context", name)
            elif isinstance(container[name], (Proxy, Node)):
                context_path = norm_path(
                    container[name].node_path, full=True) + q[ix+1:]
                break
            elif isinstance(container[name], Mapping):
                container = container[name]
        return context_path
