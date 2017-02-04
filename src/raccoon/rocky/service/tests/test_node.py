# -*- coding: utf-8 -*-
# :Project:  raccoon.rocky.service -- pairable tests
# :Created:  mer 11 gen 2017 14:08:28 CET
# :Author:   Alberto Berti <alberto@metapensiero.it>
# :License:  GNU General Public License version 3 or later
#

import pytest

from raccoon.rocky.service import WAMPNode


@pytest.mark.asyncio
async def test_primary_description(connection1, events, event_loop):

    events.define('done')
    sess = None

    n1 = WAMPNode()
    n2 = WAMPNode()

    async def when_connected(session, session_details):

        nonlocal sess
        sess = session

        await n1.node_bind('raccoon.primary.test', connection1.new_context())
        await n1.node_add('n2', n2)

        events.done.set()

    await connection1.on_connect.connect(when_connected)
    await events.done.wait()

    manager = WAMPNode.manager

    assert 'raccoon.primary.test' in manager.reg_store.uri_to_item['call']

    n1.node_context.pippo = 1

    desc = await sess.call('raccoon.primary.test')
    assert desc == {'.': {'description': {'pippo': 1},
                             'info': {
                                 'system': {'lang': 'Python', 'name': 'server'},
                                 'type': 'WAMPNode',
                                 'uri': 'raccoon.primary.test'}}}

    desc = await sess.call('raccoon.primary.test', 1)
    assert desc == {'n2': {'.': {'description': {'pippo': 1},
                                 'info': {'system': {'lang': 'Python',
                                                     'name': 'server'},
                                          'type': 'WAMPNode',
                                          'uri': 'raccoon.primary.test.n2'}}},
                    '.': {'description': {'pippo': 1},
                          'info': {'system': {'lang': 'Python', 'name': 'server'},
                                   'type': 'WAMPNode',
                                   'uri': 'raccoon.primary.test'}}}

    await n1.node_unbind()
