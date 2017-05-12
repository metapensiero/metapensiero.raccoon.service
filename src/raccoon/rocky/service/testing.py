# -*- coding: utf-8 -*-
# :Project:   raccoon.rocky.service -- testing utilitie
# :Created:   sab 26 mar 2016 14:45:53 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016, 2017 Arstecnica s.r.l.
#

import asyncio
import atexit
from contextlib import closing
from fcntl import fcntl, F_GETFL, F_SETFL
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from tempfile import mkdtemp
import time

from metapensiero import reactive
import pytest
import txaio

from .wamp.connection import Connection
from . import system, init_system


def get_next_free_tcp_port():
    """Return the next free TCP port on the ``localhost`` interface."""
    with closing(socket.socket()) as sock:
        sock.bind(('localhost', 0))
        return sock.getsockname()[1]


def launch_crossbar(directory):
    """Launch an instance of the Crossbar WAMP router.

    :param directory: the directory containing the configuration file
      (must be writable)
    """

    process = subprocess.Popen([sys.executable, '-u', '-m',
                                'crossbar.controller.cli', 'start',
                                '--cbdir', str(directory)],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Read output until a line is found that confirms the transport is
    # ready

    # set the O_NONBLOCK flag of p.stdout file descriptor:
    flags = fcntl(process.stdout, F_GETFL) # get current p.stdout flags
    fcntl(process.stdout, F_SETFL, flags | os.O_NONBLOCK)

    out = bytearray()

    max_attempts = 20
    attempts = 0
    seconds = 1
    while attempts < max_attempts:
        attempts += 1
        time.sleep(seconds)

        try:
            o = os.read(process.stdout.fileno(), 256)
            if o:
                out += o
        except BlockingIOError:
            pass

        if b"transport 'transport-001' started" in out:
            atexit.register(process.terminate)
            break
    else:
        process.kill()
        final_out = process.stdout.read()
        if final_out:
            out += final_out
        raise RuntimeError(f'Crossbar failed to start or startup detection'
                           f' failed, after {attempts*seconds} seconds:\n'
                           f'STDOUT:\n{out.decode()}\n'
                           f'STDERR:\n{process.stderr.read().decode()}')


def launch_adhoc_crossbar(config):
    """Launch an ad-hoc instance of the Crossbar WAMP router.

    This is a convenience function for testing purposes and should not
    be used in production.  It writes the given configuration in a
    temporary directory and replaces ``%(port)s`` in the configuration
    with an ephemeral TCP port.

    If no configuration is given a default configuration is used where
    only anonymous authentication is defined and the anonymous user
    has all privileges on everything.  One websocket transport is
    defined, listening on ``localhost``.

    The Crossbar process is automatically terminated and the temporary
    directory deleted when the host process terminates.

    :param config: YAML configuration for crossbar (for ``config.yaml``)
    :return: the automatically selected port
    """

    # Get the next available TCP port
    port = get_next_free_tcp_port()

    # Write the configuration file
    tempdir = Path(mkdtemp())
    atexit.register(shutil.rmtree, str(tempdir))
    config_file = tempdir / 'config.yaml'
    with config_file.open('w') as f:
        f.write(config % {'port': port})

    launch_crossbar(tempdir)

    return port


@pytest.fixture(scope='session')
def ws_url():
    port = launch_adhoc_crossbar("""\
---
version: 2
workers:
- type: router
  realms:
  - name: default
    roles:
    - name: authorized_users
      permissions:
      - uri: "*"
        allow: {call: true, publish: true, register: true, subscribe: true}
        disclose: {publisher: true, caller: true}
    - name: anonymous
      permissions:
      - uri: "*"
        allow: {call: true, publish: true, register: true, subscribe: true}
        disclose: {publisher: true, caller: true}

  transports:
  - type: websocket
    endpoint:
      type: tcp
      interface: localhost
      port: %(port)s
    auth:
      anonymous:
        type: static
        role: anonymous
      wampcra:
        type: static
        users:
          testuser:
            secret: testpass
            role: authorized_users
      ticket:
        type: static
        principals:
          user1:
            ticket: abc123
            role: authorized_users
          user2:
            ticket: abc123
            role: authorized_users
""")
    return 'ws://localhost:{}/'.format(port)


@pytest.fixture
def setup_txaio(event_loop):
    txaio.use_asyncio()
    txaio.config.loop = event_loop


@pytest.fixture
def setup_reactive(event_loop):
    reactive.get_tracker().flusher.loop = event_loop


@pytest.fixture
def init_node_system(event_loop):
    if not system.node_path:
        event_loop.run_until_complete(init_system())


@pytest.fixture
def setup_system(init_node_system, event_loop):
    system.node_context.loop = event_loop


@pytest.yield_fixture
def connection1(request, event_loop, ws_url, setup_txaio, setup_reactive,
                setup_system):
    kwargs = getattr(request, 'param', {'username': 'user1',
                                        'password': 'abc123'})
    conn = _create_connection(kwargs, event_loop, ws_url)
    yield conn
    _close_connection(conn, event_loop)


@pytest.yield_fixture
def connection2(request, event_loop, ws_url, setup_txaio, setup_reactive,
                setup_system):
    kwargs = getattr(request, 'param', {'username': 'user2',
                                        'password': 'abc123'})
    conn = _create_connection(kwargs, event_loop, ws_url)
    yield conn
    _close_connection(conn, event_loop)


def _create_connection(login, event_loop, ws_url):
    conn = Connection(ws_url, 'default', loop=event_loop)
    connect_future = asyncio.ensure_future(conn.connect(**login))
    event_loop.run_until_complete(connect_future)
    return conn


def _close_connection(connection, loop):
    loop.run_until_complete(connection.disconnect())
