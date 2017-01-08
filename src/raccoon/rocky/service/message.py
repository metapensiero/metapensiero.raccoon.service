# -*- coding: utf-8 -*-
# :Project: arstecnica.ytefas.appserver -- message
# :Created: gio 29 dic 2016 02:25:10 CET
# :Author:  Alberto Berti <alberto@metapensiero.it>
# :License: GNU General Public License version 3 or later
#

from raccoon.rocky.node import Node, Path
from .node import ServiceNode

class Message:

    source = None
    type = None
    dest = None
    misc = None

    def __init__(self, source, type_, dest=None, **kwargs):
        assert isinstance(source, ServiceNode)
        self._source = source
        self.source = source.node_info()
        self.type = type_
        if dest:
            self.dest = self._resolve_destination(dest)
        else:
            self.dest = None
        self.details = kwargs

    def __call__(self, dest=None, **kwargs):
        if dest:
            self.dest = self._resolve_destination(dest)
        self.details.update(kwargs)
        return {'msg_{}'.format(k): v for k, v in self.__dict__.items() if not
                k.startswith('_')}

    def __repr__(self):
        return ("<{cls}, type: '{type_}', src: '{src}', "
                "details: '{det}'".format(cls=self.__class__.__name__,
                                          type_=self.type,
                                          src=self.source['uri'],
                                          det=self.details))

    def _resolve_destination(self, dest):
        if isinstance(dest, Node):
            dest = str(dest.node_path)
        elif isinstance(dest, Path):
            dest = str(dest)
        else:
            dest = self._source.node_path.resolve(dest,
                                                  self._source._node_context)
        return dest

    @classmethod
    def read(cls, **kwargs):
        new = cls.__new__(cls)
        misc = {}
        for k, v in kwargs.items():
            if k.startswith('msg_'):
                new.__dict__[k[4:]] = v
            else:
                misc[k] = v
        if len(misc):
            new.__dict__['misc'] = misc
        return new

    def send(self, dest=None, **kwargs):
        data = self(dest=dest, **kwargs)
        self._source.remote(self.dest).notify(**data)
