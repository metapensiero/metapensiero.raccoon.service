# -*- coding: utf-8 -*-
# :Project:   metapensiero.raccoon.service -- wamp connection class
# :Created:   gio 24 mar 2016 20:33:15 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: © 2016, 2017, 2018 Alberto Berti
#

import logging
import signal

from arstecnica.raccoon.autobahn.client import Client
from metapensiero.signal import Signal, SignalAndHandlerInitMeta
from metapensiero.raccoon.node import WAMPNodeContext

from .session import Session

logger = logging.getLogger(__name__)


class Connection(Client, metaclass=SignalAndHandlerInitMeta):
    "A client connection, enriched with some signals."

    on_connect = Signal()
    """Signal emitted when the connection is activated and the session has
    joined the realm.
    """

    def __init__(self, url, realm, loop=None, **kwargs):
        """:param str url: a :term:`WAMP` connection url
        :param str realm: a :term:`WAMP` realm to enter
        :param loop: an optional asyncio loop

        Every other keyword argument will be passed to the underlying
        autobahn client.
        """
        super().__init__(url, realm, loop=None, **kwargs)
        self.session = None
        self.session_details = None

    def _notify_disconnect(self):
        """NOTE: This is not a coroutine but returns one."""
        try:
            return self.on_disconnect.notify(loop=self.loop)
        finally:
            self.session = None
            self.session_details = None

    async def _on_session_leave(self, details):
        return await self._notify_disconnect()

    async def connect(self, username=None, password=None):
        "Emits the :attr:`on_connect` signal."
        session, sess_details = await super().connect(username, password,
                                                      session_class=Session)
        self.session = session
        self.session_details = sess_details
        await self.on_connect.notify(session=session,
                                     session_details=sess_details,
                                     loop=self.loop)
        session.on_leave.connect(self._on_session_leave)
        return session, sess_details

    @property
    def connected(self):
        """Returns ``True`` if this connection is attached to a session."""
        return self.session is not None and self.session.is_attached()

    async def disconnect(self):
        "Emits the :attr:`on_disconnect` signal."
        await self._notify_disconnect()
        await super().disconnect()

    def new_context(self):
        """
        Return a new :class:`~metapensiero.raccoon.node.node.WAMPNodeContext`
        instance tied to this connection.
        """
        return WAMPNodeContext(loop=self.loop, wamp_session=self.session)

    @on_connect.on_connect
    async def on_connect(self, handler, subscribers, connect, notify):
        """Call handler immediately if the session is attached already."""
        if self.connected:
            res = notify(handler, session=self.session,
                         session_details=self.session_details)
        else:
            res = self.loop.create_future()
            res.set_result(None)
        connect(handler)
        return res

    on_disconnect = Signal()
    "Signal emitted when the connection is deactivated."

    @on_disconnect.on_connect
    async def on_disconnect(self, handler, subscribers, disconnect, notify):
        """Call handler immediately if the session is already attached."""
        if not self.connected:
            res = notify(handler, loop=self.loop)
        else:
            res = self.loop.create_future()
            res.set_result(None)
        disconnect(handler)
        return res

    def run(self):
        """Adds a ``SIGTERM`` handler and runs the loop until the connection
        ends or the process is killed.
        """
        try:
            self.loop.add_signal_handler(signal.SIGTERM, self.loop.stop)
        except NotImplementedError:
            # signals are not available on Windows
            pass

        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            # wait until we send Goodbye if user hit ctrl-c
            # (done outside this except so SIGTERM gets the same handling)
            pass

        # give Goodbye message a chance to go through, if we still
        # have an active session
        if self.protocol._session:
            self.loop.run_until_complete(self.protocol._session.leave())

        self.loop.close()
