# -*- coding: utf-8 -*-
# :Project: arstecnica.ytefas.appserver -- message
# :Created: gio 29 dic 2016 02:25:10 CET
# :Author:  Alberto Berti <alberto@metapensiero.it>
# :License: GNU General Public License version 3 or later
#

from raccoon.rocky.node import Node, Path
from .node import ServiceNode

class Message:

    msg_source = None
    msg_type = None
    msg_dest = None

    def __init__(self, source, type, dest=None, **kwargs):
        assert isinstance(source, ServiceNode)
        self._source = source
        self.msg_source = source.node_info()
        self.msg_type = type
        if dest:
            self.msg_dest = self._resolve_destination(dest)
        else:
            self.msg_dest = None
        self.msg_details = kwargs

    def _resolve_destination(self, dest):
        if isinstance(dest, Node):
            dest = str(dest.node_path)
        elif isinstance(dest, Path):
            dest = str(dest)
        else:
            dest = self._source.node_path.resolve(dest,
                                                  self._source._node_context)
        return dest

    def __call__(self, dest=None, **kwargs):
        if dest:
            self.msg_dest = self._resolve_destination(dest)
        self.msg_details.update(kwargs)
        return {k: v for k, v in self.__dict__.items() if not
                k.startswith('_')}

    @classmethod
    def read(cls, **kwargs):
        new = cls.__new__(cls)
        new.__dict__.update(kwargs)
        return new

    def send(self, dest=None, **kwargs):
        data = self(dest=dest, **kwargs)
        self._source.remote(self.msg_dest).notify(**data)
