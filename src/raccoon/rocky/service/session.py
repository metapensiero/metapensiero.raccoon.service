# -*- coding: utf-8 -*-
# :Project:   raccoon.rocky.service -- session
# :Created:   mar 22 nov 2016 22:36:57 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016, 2017 Arstecnica s.r.l.
#

import asyncio
import logging

from metapensiero import reactive
from metapensiero.signal import handler
from raccoon.rocky.node import call
from raccoon.rocky.node.path import Path

from .node import WAMPNode
from .message import Message, on_message
from .pairable import PairableNode
from .resolver import RolePathResolver

logger = logging.getLogger(__name__)


class PairingRequest:

    @reactive.Value
    def ready(self):
        return all(v() for v in self.location_ready.values())

    def __init__(self, locations, details=None):
        self.details = details or {}
        self.locations = locations
        self.location_ready = {l: reactive.Value(initial_value=False) for
                               l in locations}
        self.location_info = {l: None for l in locations}

    def set_location_ready(self, location, uri, role=None, **kwargs):
        self.location_ready[location].value = True
        self.location_info[location] = {'uri': uri, 'role': role}

    def serialize(self):
        return {'locations': self.location_info, 'details': self.details}


class SessionRoot(WAMPNode):
    """The role of this object is to manage a session created by the service.
    For now, it means ensuring all the parties have successfully registered
    themselves at the designed locations and to give a start to the chosen
    member.

    Usually there are two members with locations ``server`` and ``client``.

    This object is coded to work with the :class:`SessionMember` object.
    """

    status = None

    def __init__(self, locations, local_location_name, local_member_factory):
        """
        :type locations: tuple
        :param tuple locations: a tuple containing all the location names
          involved
        :type local_location_name: str
        :param str local_location_name: the location assumed by the *local*
          member
        :type local_member_factory: callable returning a
          :class:`SessionMember` instance
        :param local_member_factory: the node object class that
          will fulfill the *local* location.
        """
        super().__init__()
        self.locations = locations
        self.local_location_name = local_location_name
        self._pairing_requests = {}
        self._pairing_counter = 0
        self._pairing_requests[0] = PairingRequest(locations)
        self._local_member_factory = local_member_factory

    def _new_pairing_id(self):
        """Generate a new pairing id."""
        self._pairing_counter += 1
        res = self._pairing_counter
        return res

    @on_message('peer_ready')
    def handle_pairing_message(self, msg):
        """Listens for messages of type 'peer_ready'."""
        details = msg.details
        self._pairing_requests[details['id']].set_location_ready(**details)

    @reactive.computation
    def manage_pairings(self, comp):
        to_remove = set()
        for id, pr in self._pairing_requests.items():
            if pr.ready:
                data = pr.serialize()
                msg = Message(self, 'peer_start', **data)
                for location in pr.locations:
                    p = Path(pr.location_info[location]['uri'])
                    msg.send(p)
                to_remove.add(id)
                if id == 0:
                    logger.info("session at '%s' is now active",
                                self.node_path)
                    self.status = 'active'
        for id in to_remove:
            del self._pairing_requests[id]

    @call
    async def pairing_request(self, src_location, info, **_):
        """Start a new pairing of two or more objects."""
        pr = PairingRequest(self.locations, info)
        pr_id = self._new_pairing_id()
        self._pairing_requests[pr_id] = pr
        msg = Message(self, 'pairing_request', id=pr_id, info=info)
        for loc in self.locations:
            if loc != src_location:
                msg.send(self.node_path + loc)
        self.manage_pairings().invalidate()
        return pr_id

    @handler('on_node_bind')
    async def start(self, **_):
        """Start the bounded session."""
        member_context = self.node_context.new(location=self.local_location_name,
                                               pairing_request={'id': 0})
        local_member = self._local_member_factory(member_context)
        await self.node_add(self.local_location_name, local_member)
        self.manage_pairings()


class SessionMember(PairableNode):

    def __init__(self, context):
        assert context
        context.path_resolvers.append(RolePathResolver())
        super().__init__(context)

    @on_message('pairing_request')
    async def handle_pairing_message(self, msg):
        """Listens for messages of type 'peer_ready'"""
        await self.create_new_peer(msg.details)

    async def create_new_peer(self, details):
        raise NotImplementedError("An incoming pairing request must be handled")


async def bootstrap_session(wamp_context, service_uri, factory,
                            location_name=None, session_id=None, loop=None):
    """Helper method to start a session in the right way. The `factory` passed
    in should create an instance whose class is derived from
    :class:`SessionMember`.

    :type wamp_context: :class:`~raccoon.rocky.node.context.WAMPNodeContext`
      instance
    :param wamp_context: a node context already connected
    :param str service_uri: the path of the `ApplicationService` to call
    :param callable factory: a factory that will be called to produce the
      local member of the session
    :param str location_name: optional wanted location name for the session
      member. It is ``client`` by default. It can be changed by the service.
    :param int session_id: not used right now. It's possible use will be to
      specify a session_id to join rather than start a new one.
    :returns: an instance of `SessionMember` that is part of the session
    """
    loop = loop or asyncio.get_event_loop()
    location_name = location_name or 'client'
    session_starter = str(Path(service_uri) + 'start_session')
    wsession = wamp_context.wamp_session
    session_info = await wsession.call(session_starter, location_name,
                                       session_id)
    session_ctx = wamp_context.new(location=session_info['location'],
                                   pairing_request={'id': 0},
                                   session_id=session_info['id'])
    local_path = Path(session_info['location'], session_info['base'])
    local_session_member = factory(session_ctx)
    assert isinstance(local_session_member, SessionMember)
    await local_session_member.node_bind(local_path, session_ctx)
    return local_session_member
