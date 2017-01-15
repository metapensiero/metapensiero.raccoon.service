# -*- coding: utf-8 -*-
# :Project:   raccoon.rocky.service -- wamp session class
# :Created:   gio 24 mar 2016 20:33:15 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016, 2017 Arstecnica s.r.l.
#

import logging
import signal

from arstecnica.raccoon.autobahn.client import ClientSession
from metapensiero.signal import Signal, SignalAndHandlerInitMeta

logger = logging.getLogger(__name__)


class Session(ClientSession, metaclass=SignalAndHandlerInitMeta):
    "A client session, enriched with some signals."

    on_join = Signal()
    "Signal emitted when the session is joined."

    on_leave = Signal()
    "Signal emitted when the session is detached."

    def onJoin(self, details):
        "Emit the ``on_join`` signal."
        loop = self.config.extra['joined']._loop
        self.on_join.notify(details, loop=loop)
        super().onJoin(details)

    def onLeave(self, details):
        "Emit the ``on_leave`` signal."
        loop = self.config.extra['joined']._loop
        self.on_leave.notify(details, loop=loop)
        super().onLeave(details)
