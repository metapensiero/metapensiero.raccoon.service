# -*- coding: utf-8 -*-
# :Project:   raccoon.rocky.service -- testing utilitie
# :Created:   sab 26 mar 2016 14:45:53 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016 Arstecnica s.r.l.
#

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

    max_start_time = 10
    for count in range(20):
        time.sleep(max_start_time/20)
        try:
            o = os.read(process.stdout.fileno(), 256)
            if o:
                out += o
        except BlockingIOError:  # emacs may flag an error here, ignore it
            pass

        if b"transport 'transport-001' started" in out:
            atexit.register(process.terminate)
            break
    else:
        process.kill()
        final_out = process.stdout.read()
        if final_out:
            out += final_out
        raise RuntimeError(('Crossbar failed to start or startup detection '
                            'failed, after {start_time} seconds:'
                            '\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}').format(
                                start_time=max_start_time,
                                stdout=out.decode(),
                                stderr=process.stderr.read().decode()))


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

    The Crossbar process is automatically terminated and temporary
    directory deleted when the host process terminates.

    :param config: YAML configuration for crossbar (for
      ``config.yaml``)
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
      - uri: raccoon
        match: prefix
        allow: {call: true, publish: true, register: true, subscribe: true}
        disclose: {publisher: true, caller: true}
    - name: anonymous
      permissions:
      - uri: raccoon
        match: prefix
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

@pytest.yield_fixture
def connection1(request, event_loop, ws_url, setup_txaio, setup_reactive):
    kwargs = getattr(request, 'param', {'username': 'user1',
                                        'password': 'abc123'})
    conn = Connection(ws_url, 'default', loop=event_loop)

    event_loop.run_until_complete(conn.connect(**kwargs))
    yield conn
    event_loop.run_until_complete(conn.disconnect())


@pytest.yield_fixture
def connection2(request, event_loop, ws_url, setup_txaio, setup_reactive):
    kwargs = getattr(request, 'param', {'username': 'user2',
                                        'password': 'abc123'})
    conn = Connection(ws_url, 'default', loop=event_loop)
    event_loop.run_until_complete(conn.connect(**kwargs))
    yield conn
    event_loop.run_until_complete(conn.disconnect())
