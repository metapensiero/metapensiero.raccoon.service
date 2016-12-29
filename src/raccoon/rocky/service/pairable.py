# -*- coding: utf-8 -*-
# :Project:  raccoon.rocky.service -- pairable object
# :Created:  mar 22 nov 2016 22:36:57 CET
# :Author:   Alberto Berti <alberto@metapensiero.it>
# :License:  GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016 Arstecnica s.r.l.
#

import logging

from metapensiero.asyncio import transaction
from metapensiero.signal import Signal, handler
from .message import Message
from .node import WAMPNode

logger = logging.getLogger(__name__)


class PairableNode(WAMPNode):
    """A node subclass that implements the 'slave' side protocol for pairing two
    or more objects running in different locations. This to ensure that each
    of the paired objects will execute its 'start' method when the other peers
    are ready, and to give better addressability. Each member of the 'pair'
    can declare a role and it will be addressable by using '#role' paths from
    the others.

    The 'master' part of the protocol is implemented in the `SessionRoot`
    object.

    This object needs the service and session infrastructure to operate
    correctly.
    """

    on_info = Signal()
    """Signal used to receive 'infrastructure' messages. The messages that
    implement the pairing protocol are of type 'pairing_request', 'peer_ready'
    and 'peer_start'.
    """

    pairing_active = False
    """Flag that it's true when the pairing is correctly setup and isn't
    stopped."""

    def __init__(self, context=None):
        self.node_context = context

    def _pairable_notify_stop(self):
        role = self.node_context.get('role')
        peers = self.node_context.get('peers')
        if peers and self.pairing_active:
            for peer_role, peer_path in peers.items():
                if peer_role != role:
                    Message(self, 'peer_stop', peer_path).send(role=role)

    @handler('on_info')
    async def handle_start_message(self, *args, **kwargs):
        """When the pairing request is complete, automatically execute the 'start'
        method and inject into the context informations about available peers
        that will be used in path resolution.
        """
        msg = Message.read(**kwargs)
        if msg.msg_type == 'peer_start':
            details = msg.msg_details
            peers = {l['role']: l['uri'] for l in details['locations'].values()
                     if l['role']}
            if peers:
                self.node_context.peers = peers
            self.pairing_active = True
            logger.debug("Pairing phase completed with peers: '%s'", peers)
            await self.peer_start(details)

    @handler('on_info')
    async def handle_stop_message(self, *args, **kwargs):
        """Obey to the stop of the pairing signalled by one other peer."""
        msg = Message.read(**kwargs)
        if msg.msg_type == 'peer_stop' and self.pairing_active:
            self.pairing_active = False
            await self.peer_stop()

    @handler('on_node_registration_success')
    async def handle_registration_success(self, **_):
        """When the registration is completed, check for the existence of a
        'pairing_request' member on the node context. If that exists, either I
        must start a new pairing or acknowledge one started already. This
        depends on the presence of an 'id' property inside it. The id is
        available only when acknowledging.
        """
        pr = getattr(self.node_context, 'pairing_request', None)
        if pr and isinstance(pr, dict) and 'id' in pr:
            # this peer is the one created in response to a pairing request
            pr_id = pr['id']
        else:
            # this peer is the one who starts the pairing process
            pr_id = await self.remote('@pairing_request')(
                self.node_context.location, pr
            )
        await self.peer_init()
        msg = Message(self, 'peer_ready',
                      id=pr_id,
                      location=self.node_context.location,
                      uri=str(self.node_path),
                      role=self.node_context.get('role'))
        msg.send(self.node_path.base + 'on_info')

    async def peer_init(self):
        logger.debug("Paired object at '%s' initialized.", self.node_path)

    async def peer_start(self, start_info):
        logger.debug("Paired object at '%s' started.", self.node_path)

    async def peer_stop(self):
        logger.debug("Paired object at '%s' stopped.", self.node_path)
        self._pairable_notify_stop()
        self.pairing_active = False
        del self.node_context.peers
        async with transaction.begin(loop=self.loop):
            self.node_unbind()
