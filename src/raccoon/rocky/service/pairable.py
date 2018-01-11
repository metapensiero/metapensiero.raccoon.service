# -*- coding: utf-8 -*-
# :Project:   metapensiero.raccoon.service -- pairable object
# :Created:   mar 22 nov 2016 22:36:57 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: © 2016, 2017, 2018 Alberto Berti
#

import logging

from metapensiero.signal import handler
from metapensiero.raccoon.node import Path
from .message import Message, on_message
from .node import ContextNode

logger = logging.getLogger(__name__)


class PairableNode(ContextNode):
    """
    A node subclass that implements the *slave* side protocol for pairing two
    or more objects running in different locations. This to ensure that each
    of the paired objects will execute its :meth:`start` method when the other
    peers are ready, and to give better addressability.

    Each member of the *pair* can declare a role and it will be addressable by
    using '#role' paths from the others.

    The *master* part of the protocol is implemented by the
    :class:`~service.session.SessionRoot` object.

    This object needs the service and session infrastructure to operate
    correctly.
    """

    pairing_active = False
    """Flag that it's true when the pairing is correctly setup and isn't
    stopped."""

    def __init__(self, node_context=None):
        super().__init__()
        self.node_context = node_context

    def _expand_context(self):
        """Update the ``node_context`` of a node with informations in the
        ``pairing_request``. This complement the `ContexPathResolver`."""
        pr = self.node_context.get('pairing_request')
        if isinstance(pr, dict):
            if 'id' in pr:
                info = pr.get('info', {})
            else:
                info = pr
            if 'context' in info:
                added_context = info['context']
                for key, value in added_context.items():
                    assert isinstance(value, (str, tuple, list, Path))
                    if not isinstance(value, Path):
                        # here the string or tuple path is resolved forcibly
                        # without using the context
                        value = self.node_path.resolve(value)
                    obj = self.node_resolve(value)
                    if obj is None:
                        obj = self.remote(value)
                    self.node_context.set(key, obj)

    async def _node_bind(self, path, context=None, parent=None):
        await super()._node_bind(path, context, parent)
        self._expand_context()

    def _pairable_notify_stop(self):
        role = self.node_context.get('role')
        peers = self.node_context.get('peers')
        if peers and self.pairing_active:
            for peer_role, peer in peers.items():
                Message(self, 'peer_stop', peer).send(role=role)

    @on_message('peer_start')
    async def handle_start_message(self, msg):
        """
        When the pairing request is complete, automatically execute the
        :meth:`start` method and inject into the context information about
        available peers that will be used in path resolution.
        """
        details = msg.details
        peers = {}
        for l in details['locations'].values():
            uri = l['uri']
            role = l['role']
            if uri == self.node_path:
                peer = self
            else:
                peer = self.remote(uri)  # returns a proxy
            if role:
                peers[role] = peer
        if peers:
            # FIXME: nc.peers is still useful?
            self.node_context.peers = peers
            self.node_context.update(peers)
        logger.debug("Pairing phase completed with peers: '%s'", peers)
        self.pairing_active = True
        self.node_location.changed()
        await self.peer_start(details)

    @on_message('peer_stop')
    async def handle_stop_message(self, msg):
        """Obey to the stop of the pairing signalled by one other peer."""
        # ignore messages sent by itself
        if msg.source['uri'] == self.node_path:
            return
        self.pairing_active = False
        self.node_location.changed()
        await self.peer_stop()

    @handler('on_node_bind', end=True)
    async def init_pairing(self):
        """
        When the registration is completed, check for the existence of a
        `pairing_request` member on the node context. If that exists, either
        start a new pairing or acknowledge one started already. This depends
        on the presence of an `id` property inside it. The id is available
        only when acknowledging.
        """
        ctx = self.node_context
        pr = ctx.get('pairing_request')
        await self.peer_init()
        if pr and isinstance(pr, dict) and 'id' in pr:
            # this peer is the one created in response to a pairing request
            pr_id = pr['id']
        else:
            # this peer is the one who starts the pairing process
            pr_id = await self.remote('@pairing_request')(
                ctx.location, pr
            )
        msg = Message(self, 'peer_ready',
                      id=pr_id,
                      location=ctx.location,
                      uri=str(self.node_path),
                      role=ctx.get('role'))
        msg.send(self.node_path.base)

    async def peer_init(self):
        logger.debug("Paired object at '%s' initialized.", self.node_path)

    async def peer_start(self, start_info):
        logger.debug("Paired object at '%s' started.", self.node_path)

    async def peer_stop(self):
        logger.debug("Paired object at '%s' stopped.", self.node_path)
        self._pairable_notify_stop()
        self.pairing_active = False
        del self.node_context.peers
        await self.node_unbind()
