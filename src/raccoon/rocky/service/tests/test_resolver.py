# -*- coding: utf-8 -*-
# :Project:  metapensiero.raccoon.service -- resolver tests
# :Created:  sab 26 mar 2016 18:29:03 CET
# :Author:   Alberto Berti <alberto@metapensiero.it>
# :License:  GNU General Public License version 3 or later
#

import pytest
from metapensiero.raccoon.node.context import NodeContext
from metapensiero.raccoon.node.path import Path, PathError
from metapensiero.raccoon.node.proxy import Proxy
from metapensiero.raccoon.service.resolver import ContextPathResolver


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
