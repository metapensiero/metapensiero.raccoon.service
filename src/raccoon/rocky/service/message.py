# -*- coding: utf-8 -*-
# :Project:   raccoon.rocky.service -- message
# :Created:   gio 29 dic 2016 02:25:10 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2016, 2017 Arstecnica s.r.l.
#

from functools import wraps

from metapensiero.signal import handler
from raccoon.rocky.node import Node, Path
from .node import ServiceNode


class Message:
    """Message details carrier.

    :type source: :class:`~.node.ServiceNode` instance
    :param source: the sender of the message
    :type type_: str
    :param type_: the type of the message
    :type dest: ``None``, :class:`~raccoon.rocky.node.node.Node` or
      :class:`~raccoon.rocky.node.path.Path`
    :param dest: the destination of the message
    :param kwargs: message details
    """

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
        return ("<{cls}, type: '{type}', src: '{src}',"
                " details: '{det}'>".format(cls=self.__class__.__name__,
                                            type=self.type,
                                            src=self.source['uri'],
                                            det=self.details))

    def _resolve_destination(self, dest):
        if isinstance(dest, Node):
            dest = str(dest.node_path)
        elif isinstance(dest, Path):
            dest = str(dest)
        else:
            src = self._source
            dest = str(src.node_path.resolve(dest, src._node_context))
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
        return self._source.remote(self.dest).notify(**data)


def on_message(type_, signal='.'):
    """Decorator for an handler method, to hook only to a particular `type_`
    of message coming from a `signal`. The wrapped method will receive an
    instance of :class:`Message` as the only argument, carrying all the
    interesting details of the signal.
    """
    def wrap_func(func):

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            msg_type = kwargs.get('msg_type')
            if msg_type == type_:
                msg = Message.read(**kwargs)
                return func(self, msg)

        return handler(signal)(wrapper)

    return wrap_func
