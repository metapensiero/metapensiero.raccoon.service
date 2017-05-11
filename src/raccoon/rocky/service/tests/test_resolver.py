# -*- coding: utf-8 -*-
# :Project:  raccoon.rocky.service -- resolver tests
# :Created:  sab 26 mar 2016 18:29:03 CET
# :Author:   Alberto Berti <alberto@metapensiero.it>
# :License:  GNU General Public License version 3 or later
#

import pytest
from raccoon.rocky.node.context import NodeContext
from raccoon.rocky.node.path import Path, PathError
from raccoon.rocky.node.proxy import Proxy
from raccoon.rocky.service.resolver import ContextPathResolver


def test_resolve():

    nc = NodeContext()
    p = Path('com.example')
    with pytest.raises(PathError):
        p.resolve('#pippo')

    with pytest.raises(PathError):
        p.resolve('@pippo')

    with pytest.raises(PathError):
        p.resolve('#pippo', nc)

    nc.path_resolvers.append(ContextPathResolver())
    nc.update({
        'controller': Proxy(None, Path('a.path.to.the.controller')),
        'view': Proxy(None, Path('a.path.to.the.view')),
        'context': Proxy(None, Path('a.path.to.the.controller'))
    })

    assert str(p.resolve('#controller', nc)) == 'a.path.to.the.controller'
    assert str(p.resolve('#view', nc)) == 'a.path.to.the.view'
    assert str(p.resolve('#view.foo', nc)) == 'a.path.to.the.view.foo'
    assert str(p.resolve('#', nc)) == 'a.path.to.the.controller'

    with pytest.raises(PathError):
        p.resolve('#other.foo')
