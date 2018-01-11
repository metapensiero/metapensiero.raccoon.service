# -*- coding: utf-8 -*-
# :Project:   metapensiero.raccoon.service -- user
# :Created:   ven 23 dic 2016 16:07:37 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: © 2016, 2017, 2018 Alberto Berti
#

from .node import WAMPNode


class User(WAMPNode):

    def __init__(self, user_id, login, full_name, source):
        super().__init__()
        self.user_id = user_id
        self.login = login
        self.full_name = full_name
        self.source = source
