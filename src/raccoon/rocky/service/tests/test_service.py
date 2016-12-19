# -*- coding: utf-8 -*-
# :Project:  raccoon.rocky.service -- service tests
# :Created:  sab 26 mar 2016 18:29:03 CET
# :Author:   Alberto Berti <alberto@metapensiero.it>
# :License:  GNU General Public License version 3 or later
#

import pytest
from metapensiero.signal import Signal, handler
from raccoon.rocky.node import Path

from raccoon.rocky.node import WAMPNode
from raccoon.rocky.node.wamp import call
from raccoon.rocky.service.service import BaseService, ApplicationService
from raccoon.rocky.service.session import SessionMember, bootstrap_session

@pytest.mark.asyncio
async def test_start_service(connection1, event_loop):

    test_data = {'start': False}

    class MyService(BaseService):

        async def start_service(self, path, context):
            test_data['start'] = True

    my = MyService('raccoon.test.myservice')
    await my.set_connection(connection1)

    assert test_data['start'] is True


@pytest.mark.asyncio
async def test_double_services(connection1, connection2, event_loop, events):

    events.define('ping', 'pong', 'service1', 'service2')

    class Service(BaseService):

        ping = Signal()
        pong = Signal()

        @handler('@service2.pong')
        def on_pong(self, details):
            events.pong.set()


        @handler('@service1.ping')
        def on_ping(self, details):
            events.ping.set()
            self.pong.notify()

        @handler('on_start')
        def _set_started_event(self, **_):
            events[self.node_name].set()

    base = Path('raccoon.test')

    s1 = Service(Path('service1', base=base))
    await s1.set_connection(connection1)
    s2 = Service(Path('service2', base=base))
    await s2.set_connection(connection2)

    # wait for services to be ready
    await events.wait_for(events.service1, 5)
    await events.wait_for(events.service2, 5)
    assert events.service1.is_set()
    assert events.service2.is_set()
    assert s1.node_registered
    assert s2.node_registered


    # run the notification
    s1.ping.notify()
    await events.wait(timeout=5)
    assert events.ping.is_set()
    assert events.pong.is_set()


@pytest.mark.asyncio
async def test_application_service(connection1, connection2, event_loop,
                                   events):

    import asyncio
    assert event_loop is asyncio.get_event_loop()
    assert connection1.loop is event_loop
    assert connection2.loop is event_loop
    events.define('app_started', 'start_session', 'start_session2',)

    class MyAppService(ApplicationService):

        @handler('on_start')
        def _set_started_event(self, **_):
            events['app_started'].set()

    class MyApplication(SessionMember):

        def __init__(self, context):
            super().__init__(context)
            self._counter = 0

        @call
        def inc_counter(self, details):
            self._counter += 1
            return self._counter

    class TestClient(SessionMember):
        pass

    s1 = MyAppService(MyApplication, Path('raccoon.appservice'))
    await s1.set_connection(connection1)
    await events.wait_for(events.app_started, 5)
    tc = await bootstrap_session(connection2.new_context(),
                                 'raccoon.appservice', TestClient,
                                 'test')
    events.start_session.set()
    assert 'location' in tc.node_context and tc.node_context.location == 'test'
    counter = await tc.remote('@server').inc_counter()
    assert counter == 1
    counter = await tc.remote('@server').inc_counter()
    assert counter == 2
    # now create a new session
    tc2 = await bootstrap_session(connection2.new_context(),
                                 'raccoon.appservice', TestClient,
                                 'test')
    events.start_session2.set()
    assert 'location' in tc.node_context and tc.node_context.location == 'test'
    assert tc.node_context.session_id != tc2.node_context.session_id
    assert str(tc.node_path) != str(tc2.node_path)
    counter = await tc2.remote('@server').inc_counter()
    assert counter == 1
    await events.wait(timeout=5)
