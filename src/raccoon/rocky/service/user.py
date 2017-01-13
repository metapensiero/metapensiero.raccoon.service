# -*- coding: utf-8 -*-
# :Project: raccoon.rocky.service -- user
# :Created: ven 23 dic 2016 16:07:37 CET
# :Author:  Alberto Berti <alberto@metapensiero.it>
# :License: GNU General Public License version 3 or later
#

from raccoon.rocky.node.wamp import WAMPInitMeta
from .node import WAMPNode


ANONYMOUS = None


class UserMeta(WAMPInitMeta):

    def __call__(cls, user_id=None, login=None, user_name=None,
                 source=None):
        global ANONYMOUS
        if user_id:
            if not login and (not user_name or
                (user_name and user_name.lower() == 'anonymous')):
                raise ValueError("Some fields are missing")
            result = super().__call__(user_id, login, user_name, source)
        else:
            if not ANONYMOUS:
                ANONYMOUS = super().__call__()
            result = ANONYMOUS
        return result


class User(WAMPNode, metaclass=UserMeta):

    def __init__(self, user_id=None, login=None, user_name=None,
                 source=None):
        self.user_id = user_id
        self.login = login
        self.user_name = user_name
        self.source = source


AnonymousUser = User(user_name='Anonymous User')
