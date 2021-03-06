# -*- coding: utf-8 -*-
# :Project:   metapensiero.raccoon.service -- service
# :Created:   gio 24 mar 2016 20:33:15 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: © 2016, 2017, 2018 Alberto Berti
#

import logging

from metapensiero.signal import handler, Signal
from metapensiero.raccoon.node import WAMPNodeContext
from metapensiero.raccoon.node.path import Path
from metapensiero.raccoon.node.wamp import call

from .node import ContextNode
from .session import SessionRoot
from . import system

logger = logging.getLogger(__name__)


class BaseService(ContextNode):
    """A simple class tailored to the needs of setting up some tree of
    endpoints immediately available as soon as the wamp connection is
    established.
    """

    on_start = Signal()
    """Signal emitted when the service starts. This happens when the
    connection has successfully joined the realm and the
    ``session.is_attached()`` is ``True`` rather than a simple TCP
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
        :type node_path: an instance of :class:`~metapensiero.raccoon.node.path.Path`
        :param node_context: An optional parent context
        :type node_context: An instance of
          :class:`~metapensiero.raccoon.node.context.WAMPContext`
        """
        super().__init__()
        self._connection = None
        self._tmp_path = node_path
        if node_context:
            context = node_context.new()
        else:
            context = WAMPNodeContext()
        context.chain(system.node_context)
        self._tmp_context = context
        self.started = False

    @property
    def connection(self):
        """
        :param connection: The associated connection
        :type connection: A :class:`~.wamp.connection.Connection`
        """
        return self._connection

    async def set_connection(self, connection):
        """Set the wamp connection."""
        self._connection = connection
        self._tmp_context.loop = connection.loop
        await connection.on_connect.connect(self._on_connection_connected)

    async def _on_connection_connected(self, session, session_details,
                                       **kwargs):
        path, context = self._tmp_path, self._tmp_context
        del self._tmp_path, self._tmp_context
        context.wamp_session = session
        context.wamp_details = session_details
        await self.node_bind(path, context)
        await self.start_service(path, context)
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
        logger.debug("Service at %r started", self.node_path)


class ApplicationService(BaseService):
    """
    A service that publishes an API for the creation of long-running contexes.

    Each time a long-running session starts, it executes the supplied
    factory with a tailored context.

    :param factory: a class or method to execute per-session
    :param node_path: Path of the service :term:`WAMP` path
    :type node_path: an instance of :class:`~metapensiero.raccoon.node.path.Path`
    :param context: An optional parent context
    :type context: An instance of
      :class:`~metapensiero.raccoon.node.context.WAMPContext`
    :results: a dictionary containing initial session info.
    """

    SESSION_CLASS = SessionRoot
    """The type of the session to instantiate when `~.create_session` is
    called."""

    location_name = system.name

    on_session_stopped = Signal()
    """The `~metapensiero.signal.atom.Signal` that is fired each time a session is
    reached a ``stopped`` state."""

    def __init__(self, factory, node_path, node_context=None):
        super().__init__(node_path, node_context=node_context)
        self._next_session_num = 1
        self._sessions = {}
        self._factory = factory

    def _next_session_id(self):
        res = self._next_session_num
        self._next_session_num += 1
        return str(res)

    async def _create_session(self, session_id, from_location,
                              client_details=None):
        session_ctx = self.node_context.new(service=self,
                                            session_id=session_id)
        session_ctx.session_id = session_id
        session_path = Path(self.node_path + session_id)
        session_path.base = session_path
        sess = self.SESSION_CLASS(locations=[from_location, self.location_name],
                                  local_location_name=self.location_name,
                                  local_member_factory=self._factory,
                                  client_details=client_details)
        await sess.node_bind(session_path, session_ctx, self)
        return sess

    @call
    async def start_session(self, from_location, session_id=None,
                            details=None):
        """The entrypoint for this service. This should be called by the client to
        start a session that will establish and orchestrate further
        communication.
        """
        if (session_id and session_id not in self._sessions) or \
           not session_id:
            session_id = self._next_session_id()
            session_root = sr = await self._create_session(session_id,
                                                           from_location,
                                                           details)
            self._sessions[session_id] = session_root
        else:
            session_root = sr = self._sessions[session_id]
        return {
            'location': from_location,
            'base': str(sr.node_path),
            'id': sr.node_context.session_id
        }

    @handler('on_session_stopped')
    def _remove_session(self, session):
        del self._sessions[session.node_name]
