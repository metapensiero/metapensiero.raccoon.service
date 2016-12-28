# -*- coding: utf-8 -*-
# :Project:   raccoon.rocky.service -- Service classes for Rocky
# :Created:   gio 24 mar 2016, 19.20.15, CET
# :Author:    Alberto Berti <alberto@arstecnica.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016 Arstecnica s.r.l.
#

from metapensiero import reactive
from metapensiero.reactive.flush.asyncio import AsyncioFlushManager

reactive.set_flusher_factory(AsyncioFlushManager)

from raccoon.rocky.node import NodeContext
from .node import Node, WAMPNode
from .pairable import PairableNode
from .service import BaseService, ApplicationService
from .session import SessionRoot, SessionMember, bootstrap_session
from .user import User, AnonymousUser
from . import system


def init_system(*, context=None, loop=None):
    context = context or NodeContext(loop=loop)
    system.node_bind('system', context)
    system.users = Node()
    system.users.anonymous = AnonymousUser
