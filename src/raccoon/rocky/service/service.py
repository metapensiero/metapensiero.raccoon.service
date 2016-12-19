# -*- coding: utf-8 -*-
# :Project:  raccoon.rocky.service -- service
# :Created:  gio 24 mar 2016 20:33:15 CET
# :Author:   Alberto Berti <alberto@metapensiero.it>
# :License:  GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016 Arstecnica s.r.l.
#

import logging

from metapensiero.asyncio import transaction
from metapensiero.signal import Signal
from raccoon.rocky.node import WAMPNode, WAMPNodeContext
from raccoon.rocky.node.path import Path
from raccoon.rocky.node.wamp import call

from .session import SessionRoot

logger = logging.getLogger(__name__)


class BaseService(WAMPNode):
    """A simple class tailored to the needs of setting up some tree of
    endpoints immediately available as soon as the wamp connection is
    established.
    """

    on_start = Signal()
    """Signal emitted when the service starts. This happens when the
    connection has successfully joined the realm and the
    ``session.is_attached()`` is ``True`` rather than a simple tcp
    connection.
    """

    @on_start.on_connect
    async def on_start(self, handler, subscribers, connect):
        """Call handler immediately if the service is started already"""
        if self.started:
            await connect.notify(handler, self.node_path, self.node_context)
        connect(handler)

    def __init__(self, node_path, node_context=None):
        """
        :param node_path: Path of the service :term:`WAMP` path
        :type node_path: an instance of :class:`~raccoon.rocky.node.path.Path`
        :param node_context: An optional parent context
        :type node_context: An instance of
          :class:`~raccoon.rocky.node.context.WAMPContext`
        """
        self._connection = None
        self._tmp_path = node_path
        if node_context:
            context = node_context.new()
        else:
            context = WAMPNodeContext()
        self._tmp_context = context
        self.started = False

    @property
    def connection(self):
        """
        :param connection: The associated connection
        :type connection: A :class:`~.wamp.connection.Connection`
        """
        return self._connection

    def set_connection(self, connection):
        """NOTE: This is not a coroutine but returns one, giving the chance to the
        calling context to wait on it."""
        self._connection = connection
        self._tmp_context.loop = connection.loop
        self.node_bind(self._tmp_path, self._tmp_context)
        del self._tmp_path, self._tmp_context
        # this is a coroutine but we cant await here, this method probably
        # gets called inside an __init__(). the signal machinery schedules it
        # anyway
        res = connection.on_connect.connect(self._on_connection_connected)
        return res

    async def _on_connection_connected(self, session, session_details,
                                       **kwargs):
        self.node_context.wamp_session = session
        self.node_context.wamp_details = session_details
        await self.start_service(self.node_path, self.node_context)
        self.started = True
        await self.on_start.notify(local_path=self.node_path,
                                   local_context=self.node_context)

    async def start_service(self, path, context):
        """Start this service. Execute the :py:meth:`~.node.Node.bind` on the
        passed in arguments and register the instance on the
        :term:`WAMP` network Called by the default ``on_start`` signal
        handler.

        :param path: Dotted string or sequence of the :term:`WAMP`  path.
        :param context: The execution context.
        :type context: A :py:class:`.context.GlobalContext`

        """
        async with transaction.begin():
            self.node_register()
            # ensure that all the registrations have completed after this
            # point
        logger.debug("Service at %r started" % self.node_path)


class ApplicationService(BaseService):
    """A service that publishes an api for the creation of long-running contexes.

    Each time a long-running session starts, it executes the supplied
    factory with a tailored context.
    """

    location_name = 'server'

    def __init__(self, factory, node_path, node_context=None):
        """
        :param path: Path of the service :term:`WAMP` path
        :type path: an instance of :class:`~raccoon.rocky.node.path.Path`
        :param factory: a class or method to execute per-session
        :param context: An optional parent context
        :type context: An instance of
          :class:`~raccoon.rocky.node.context.WAMPContext`
        """
        super().__init__(node_path, node_context=node_context)
        self._next_session_num = 1
        self._sessions = {}
        self._factory = factory

    def _next_session_id(self):
        res = self._next_session_num
        self._next_session_num += 1
        return str(res)

    async def _create_session(self, session_id, from_location):
        session_ctx = self.node_context.new()
        session_ctx.service = self
        session_ctx.session_id = session_id
        session_path = Path(self.node_path + session_id)
        session_path.base = session_path
        async with transaction.begin():
            sess = SessionRoot(session_path, session_ctx,
                               locations=[from_location, self.location_name],
                               local_location_name=self.location_name,
                               local_member_factory=self._factory)
        return sess

    @call
    async def start_session(self, from_location, session_id=None,
                            details=None):
        if (session_id and session_id not in self._sessions) or \
           not session_id:
            session_id = self._next_session_id()
            session_root = sr = await self._create_session(session_id,
                                                           from_location)
            self._sessions[session_id] = session_root
        else:
            session_root = sr = self._sessions[session_id]
        return {
            'location': from_location,
            'base': str(sr.node_path),
            'id': sr.node_context.session_id
        }
