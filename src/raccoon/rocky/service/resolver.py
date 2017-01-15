# -*- coding: utf-8 -*-
# :Project:   raccoon.rocky.service -- role path resolver
# :Created:   dom 18 dic 2016 01:59:44 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016, 2017 Arstecnica s.r.l.
#

from raccoon.rocky.node.path import norm_path, PathError


class RolePathResolver:
    """
    Extend the path resolution machinery with a way to automatically resolve
    peers from their role name.

    This uses a member `peers` which is present on the context after pairing
    completes successfully, defined by :class:`~.node.PairableNode`.
    """

    def __call__(self, path, query, context):
        peers = context.get('peers')
        if peers and query[0].startswith('#') and len(query[0]) > 1:
            name = query[0][1:]
            if name not in peers:
                raise PathError("Asked to resolve a role '%s' but it's not in"
                                " the peers", name)
            peer_path = norm_path(peers[query[0][1:]])
            return peer_path + query[1:]
