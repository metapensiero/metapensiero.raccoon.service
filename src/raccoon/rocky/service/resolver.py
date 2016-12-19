# -*- coding: utf-8 -*-
# :Project:  raccoon.rocky.service -- role path resolver
# :Created:  dom 18 dic 2016 01:59:44 CET
# :Author:   Alberto Berti <alberto@metapensiero.it>
# :License:  GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016 Arstecnica s.r.l.
#

from raccoon.rocky.node.path import norm_path, PathError


class RolePathResolver:
    """Extend the path resolution machinery with a way to automatically resolve
    peers from their role name. This uses a variable 'peers' which is present
    on the context after pairing completes successfully. It's defined in
    `PairableNode`.
    """

    def __call__(self, path, to_resolve, context):
        peers = context.get('peers')
        if peers and to_resolve[0].startswith('#') and len(to_resolve[0]) > 1:
            name = to_resolve[0][1:]
            if name not in peers:
                raise PathError("Asked to resolve a role '%s' but it's not in"
                                " the peers", name)
            peer_path = norm_path(peers[to_resolve[0][1:]])
            return peer_path + to_resolve[1:]
