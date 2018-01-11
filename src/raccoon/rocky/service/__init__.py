# -*- coding: utf-8 -*-
# :Project:   metapensiero.raccoon.service -- Service classes for Rocky
# :Created:   gio 24 mar 2016, 19.20.15, CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: © 2016, 2017, 2018 Alberto Berti
#

from metapensiero import reactive
from metapensiero.reactive.flush.asyncio import AsyncioFlushManager

reactive.set_flusher_factory(AsyncioFlushManager)

from raccoon.rocky.node import NodeContext
from .message import on_message, Message
from .node import ContextNode, Node, WAMPNode, when_node
from .pairable import PairableNode
from .service import BaseService, ApplicationService
from .session import SessionRoot, SessionMember, bootstrap_session
from .user import User
from . import system


async def init_system(*, context=None, loop=None):
    context = context or NodeContext(loop=loop)
    await system.node_bind('system', context)
