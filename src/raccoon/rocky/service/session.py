# -*- coding: utf-8 -*-
# :Project:  raccoon.rocky.service -- session
# :Created:  mar 22 nov 2016 22:36:57 CET
# :Author:   Alberto Berti <alberto@metapensiero.it>
# :License:  GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016 Arstecnica s.r.l.
#

import asyncio
import logging

from metapensiero import reactive
from metapensiero.asyncio import transaction
from metapensiero.signal import Signal, handler
from raccoon.rocky.node import call
from raccoon.rocky.node.path import Path

from .node import WAMPNode
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
    """The role of this object is to manage a session created by the service. For
    now, it means ensure all the parties have successfully registered
    themselves at the designed locations an to give a start to the chosen
    member.

    Usually there are two members with the locations ``server`` and ``client``.

    This object is coded to work with the ``SessionMember`` object.
    """

    on_info = Signal()
    status = None

    def __init__(self, session_base_path, session_context, locations,
                 local_location_name, local_member_factory):
        """
        :param `Service` service: the service running this session
        :param str session_base_path: a string with the uri of this session or a
          `Path` instance containing the same information
        :param `WAMPNodeContext` session_context: a context object with connection
          infos
        :param tuple locations: a tuple containing all the location names involved
        :param str local_location_name: the location assumed by the *local* member
        :param SessionMember local_member_factory: the node object class that
          will fullfill the *local* location.
        """
        self.locations = locations
        self.local_location_name = local_location_name
        self._pairing_requests = {}
        self._pairing_counter = 0
        self.node_bind(session_base_path, session_context,
                       session_context.service)
        self._pairing_requests[0] = PairingRequest(locations)
        member_context = session_context.new(location=local_location_name,
                                             pairing_request={'id': 0})
        local_member = local_member_factory(member_context)
        setattr(self, local_location_name, local_member)
        self.manage_pairings()

    def _new_pairing_id(self):
        """Generate a new pairing id"""
        self._pairing_counter += 1
        res = self._pairing_counter
        return res

    @handler('on_info')
    def handle_pairing_message(self, *args, **kwargs):
        """Listens for messages of type 'peer_ready'"""
        msg_type = kwargs.get('msg_type', None)
        if msg_type == 'peer_ready':
            details = kwargs['msg_details']
            self._pairing_requests[details['id']].set_location_ready(**details)

    @reactive.computation
    def manage_pairings(self, comp):
        to_remove = set()
        for id, pr in self._pairing_requests.items():
            if pr.ready:
                data = pr.serialize()
                msg = {
                    'msg_type': 'peer_start',
                    'msg_details': data,
                }
                for location in pr.locations:
                    p = Path(pr.location_info[location]['uri']) + 'on_info'
                    self.remote(p).notify(**msg)
                to_remove.add(id)
                if id == 0:
                    logger.info("session at '%s' is now active", self.node_path)
                    self.status = 'active'
        for id in to_remove:
            del self._pairing_requests[id]

    @call
    async def pairing_request(self, src_location, info, **_):
        pr = PairingRequest(self.locations, info)
        pr_id = self._new_pairing_id()
        self._pairing_requests[pr_id] = pr
        msg = {
            'msg_type': 'pairing_request',
            'msg_details': {
                'id': pr_id,
                'info': info
            }
        }
        for loc in self.locations:
            if loc != src_location:
                self.remote(self.node_path + loc).on_info.notify(**msg)
        self.manage_pairings().invalidate()
        return pr_id


class SessionMember(PairableNode):

    def __init__(self, context):
        assert context
        context.path_resolvers.append(RolePathResolver())
        super().__init__(context)

    @handler('on_info')
    async def handle_pairing_message(self, *args, **kwargs):
        """Listens for messages of type 'peer_ready'"""
        msg_type = kwargs.get('msg_type', None)
        if msg_type == 'pairing_request':
            details = kwargs['msg_details']
            await self.create_new_peer(details)

    async def create_new_peer(self, details):
        raise NotImplementedError("An incoming pairing request must be handled")


async def bootstrap_session(wamp_context, service_uri, factory,
                            location_name=None, session_id=None, loop=None):
    """Helper method to start a session in the right way. The factory passed in
    should create an instance which whose class is derived from
    `SessionMember`.

    :param `WAMPNodeContext` wamp_context: a node context already connected
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
    async with transaction.begin(loop):
        local_session_member = factory(session_ctx)
        assert isinstance(local_session_member, SessionMember)
        local_session_member.node_bind(local_path, session_ctx)
    return local_session_member
