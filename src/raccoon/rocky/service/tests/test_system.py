# -*- coding: utf-8 -*-
# :Project: raccoon.rocky.service -- system/node tests
# :Created: ven 23 dic 2016 22:19:36 CET
# :Author:  Alberto Berti <alberto@metapensiero.it>
# :License: GNU General Public License version 3 or later
#

import pytest

from metapensiero import reactive
from raccoon.rocky.node import NodeContext
from raccoon.rocky.service import system, Node


@pytest.mark.asyncio
async def test_system_location(init_node_system, event_loop, setup_reactive):
    assert len(system.NODE_LOCATION) == 1

    n = Node()
    await n.node_bind('foo.bar', NodeContext(loop=event_loop))
    assert len(system.NODE_LOCATION) == 2
    assert n.node_resolve('foo.bar') is n
    assert n.node_resolve('system') is system

    calls = 0

    def depend_on_n(comp):
        nonlocal calls
        if n.node_path:
            n.node_depend()
        calls += 1

    tracker = reactive.get_tracker()
    computation = tracker.reactive(depend_on_n)

    assert calls == 1

    await n.node_unbind()
    assert len(system.NODE_LOCATION) == 1

    assert computation.invalidated or calls == 2
