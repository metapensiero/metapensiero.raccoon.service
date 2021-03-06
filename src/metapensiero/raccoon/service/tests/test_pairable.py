# -*- coding: utf-8 -*-
# :Project:  metapensiero.raccoon.service -- pairable tests
# :Created:  sab 26 mar 2016 18:29:03 CET
# :Author:   Alberto Berti <alberto@metapensiero.it>
# :License:  GNU General Public License version 3 or later
#

import pytest
from metapensiero.signal import handler
from metapensiero.raccoon.node import Path

from metapensiero.raccoon.node.wamp import call
from metapensiero.raccoon.service.service import ApplicationService
from metapensiero.raccoon.service.session import SessionMember, bootstrap_session
from metapensiero.raccoon.service.pairable import PairableNode


@pytest.mark.asyncio
async def test_role_paths(connection1, connection2, event_loop,
                          events):

    events.define('app_started', 'start_session', 'view_started',
                  'bello_started')

    class MyAppService(ApplicationService):

        @handler('on_start')
        def _set_started_event(self):
            events['app_started'].set()

    class MyApplication(SessionMember):

        async def create_new_peer(self, details):
            assert 'id' in details
            foo = TestPairable(
                node_context=self.node_context.new(
                    pairing_request=details,
                    role='view'
                )
            )
            await self.node_add('foo', foo)

    class TestPairable(PairableNode):

        _counter = 0

        @call
        def inc_counter(self, details):
            self._counter += 1
            return self._counter

        async def peer_start(self, start_info):
            events[self.node_context.role + '_started'].set()
            if self.node_context.role == 'view':
                await self.remote('#bello').inc_counter()
                await self.remote('#bello').inc_counter()

    class TestClient(SessionMember):

        async def peer_start(self, start_info):
            # it should work w/o transaction
            bar = TestPairable(
                node_context=self.node_context.new(
                    pairing_request={
                        'context': {
                            'from_context': str(self.node_path)
                        }
                    },
                    role='bello'
                )
            )
            await self.node_add('bar', bar)
            events.start_session.set()

    s1 = MyAppService(MyApplication, Path('raccoon.appservice'))
    await s1.set_connection(connection1)
    await events.wait_for(events.app_started, 5)
    assert events.app_started.is_set()
    tc = await bootstrap_session(connection2.new_context(),
                                 'raccoon.appservice', TestClient,
                                 'test')
    await events.wait(timeout=5)
    assert events.start_session.is_set()
    foo_counter = await tc.bar.remote('#view').inc_counter()
    assert foo_counter == 1
    assert tc.bar._counter == 2
    assert ('from_context' in tc.bar.node_context and
            tc.bar.node_context.from_context.node_path == tc.node_path)
    foo = tc.bar.node_resolve('#view')
    assert ('from_context' in foo.node_context and
            foo.node_context.from_context.node_path == tc.node_path)
    await s1.node_unbind()
    await tc.node_unbind()
