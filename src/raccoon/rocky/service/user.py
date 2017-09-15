# -*- coding: utf-8 -*-
# :Project:   raccoon.rocky.service -- user
# :Created:   ven 23 dic 2016 16:07:37 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016, 2017 Arstecnica s.r.l.
#

from .node import WAMPNode


class User(WAMPNode):

    def __init__(self, user_id, login, full_name, source):
        super().__init__()
        self.user_id = user_id
        self.login = login
        self.full_name = full_name
        self.source = source
