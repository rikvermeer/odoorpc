# -*- coding: UTF-8 -*-
##############################################################################
#
#    OdooRPC
#    Copyright (C) 2014 Sébastien Alix.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""This module provides `Connector` classes to communicate with an `Odoo`
server with the `JSON-RPC` protocol or through simple HTTP requests.

Web controllers of `Odoo` expose two kinds of methods: `json` and `http`.
These methods can be accessed from the connectors of this module.
"""
import sys
# Python 2
if sys.version_info[0] < 3:
    from urllib2 import build_opener, HTTPCookieProcessor
    from cookielib import CookieJar
# Python >= 3
else:
    from urllib.request import build_opener, HTTPCookieProcessor
    from http.cookiejar import CookieJar

from odoorpc.rpc import error, jsonrpclib
from odoorpc.tools import v


class Connector(object):
    """Connector base class defining the interface used
    to interact with a server.
    """
    def __init__(self, host, port=8069, timeout=120, version=None):
        self.host = host
        try:
            int(port)
        except ValueError:
            txt = "The port '{0}' is invalid. An integer is required."
            txt = txt.format(port)
            raise error.ConnectorError(txt)
        else:
            self.port = int(port)
        self._timeout = timeout
        self.version = version

    @property
    def ssl(self):
        """Return `True` if SSL is activated."""
        return False

    @property
    def timeout(self):
        """Return the timeout."""
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        """Set the timeout."""
        self._timeout = timeout


class ConnectorJSONRPC(Connector):
    """Connector class using the `JSON-RPC` protocol.

    .. doctest::
        :options: +SKIP

        >>> from odoorpc import rpc
        >>> cnt = rpc.ConnectorJSONRPC('localhost', port=8069)

    .. doctest::
        :hide:

        >>> from odoorpc import rpc
        >>> cnt = rpc.ConnectorJSONRPC(HOST, port=PORT)

    Open a user session:

    .. doctest::
        :options: +SKIP

        >>> cnt.proxy_json.web.session.authenticate(db='db_name', login='admin', password='password')
        {'jsonrpc': '2.0', 'id': 202516757,
         'result': {'username': 'admin', 'user_context': {'lang': 'fr_FR', 'tz': 'Europe/Brussels', 'uid': 1},
         'db': 'db_name', 'company_id': 1, 'uid': 1, 'session_id': '308816f081394a9c803613895b988540'}}

    .. doctest::
        :hide:
        :options: +NORMALIZE_WHITESPACE

        >>> from pprint import pprint as pp
        >>> pp(cnt.proxy_json.web.session.authenticate(db=DB, login=USER, password=PWD))
        {'id': ...,
         'jsonrpc': '2.0',
         'result': {'company_id': 1,
                    'db': ...,
                    'session_id': ...,
                    'uid': 1,
                    'user_context': ...,
                    'username': 'admin'}}

    Read data of a partner:

    .. doctest::
        :options: +SKIP

        >>> cnt.proxy_json.web.dataset.call(model='res.partner', method='read', args=[[1]])
        {'jsonrpc': '2.0', 'id': 454236230,
         'result': [{'id': 1, 'comment': False, 'ean13': False, 'property_account_position': False, ...}]}

    .. doctest::
        :hide:

        >>> data = cnt.proxy_json.web.dataset.call(model='res.partner', method='read', args=[[1]])
        >>> 'jsonrpc' in data and 'id' in data and 'result' in data
        True

    You can send requests this way too:

    .. doctest::
        :options: +SKIP

        >>> cnt.proxy_json['/web/dataset/call'](model='res.partner', method='read', args=[[1]])
        {'jsonrpc': '2.0', 'id': 328686288,
         'result': [{'id': 1, 'comment': False, 'ean13': False, 'property_account_position': False, ...}]}

    .. doctest::
        :hide:

        >>> data = cnt.proxy_json['/web/dataset/call'](model='res.partner', method='read', args=[[1]])
        >>> 'jsonrpc' in data and 'id' in data and 'result' in data
        True

    Or like this:

    .. doctest::
        :options: +SKIP

        >>> cnt.proxy_json['web']['dataset']['call'](model='res.partner', method='read', args=[[1]])
        {'jsonrpc': '2.0', 'id': 102320639,
         'result': [{'id': 1, 'comment': False, 'ean13': False, 'property_account_position': False, ...}]}

    .. doctest::
        :hide:

        >>> data = cnt.proxy_json['web']['dataset']['call'](model='res.partner', method='read', args=[[1]])
        >>> 'jsonrpc' in data and 'id' in data and 'result' in data
        True
    """
    def __init__(self, host, port=8069, timeout=120, version=None,
                 deserialize=True):
        super(ConnectorJSONRPC, self).__init__(host, port, timeout, version)
        self.deserialize = deserialize
        # One URL opener (with cookies handling) shared between
        # JSON and HTTP requests
        cookie_jar = CookieJar()
        self._opener = build_opener(
            HTTPCookieProcessor(cookie_jar))
        self._proxy_json, self._proxy_http = self._get_proxies()

    def _get_proxies(self):
        """Returns the :class:`ProxyJSON <odoorpc.rpc.jsonrpclib.ProxyJSON>`
        and :class:`ProxyHTTP <odoorpc.rpc.jsonrpclib.ProxyHTTP>` instances
        corresponding to the server version used.
        """
        proxy_json = jsonrpclib.ProxyJSON(
            self.host, self.port, self._timeout,
            ssl=self.ssl, deserialize=self.deserialize, opener=self._opener)
        proxy_http = jsonrpclib.ProxyHTTP(
            self.host, self.port, self._timeout,
            ssl=self.ssl, opener=self._opener)
        # Detect the server version
        if self.version is None:
            result = proxy_json.web.webclient.version_info()['result']
            if 'server_version' in result:
                self.version = result['server_version']
        return proxy_json, proxy_http

    @property
    def proxy_json(self):
        """Return the JSON proxy."""
        return self._proxy_json

    @property
    def proxy_http(self):
        """Return the HTTP proxy."""
        return self._proxy_http

    @property
    def timeout(self):
        """Return the timeout."""
        return self._proxy_json._timeout

    @timeout.setter
    def timeout(self, timeout):
        """Set the timeout."""
        self._proxy_json._timeout = timeout
        self._proxy_http._timeout = timeout


class ConnectorJSONRPCSSL(ConnectorJSONRPC):
    """Connector class using the `JSON-RPC` protocol over `SSL`.

    .. doctest::
        :options: +SKIP

        >>> from odoorpc import rpc
        >>> cnt = rpc.ConnectorJSONRPCSSL('localhost', port=8069)

    .. doctest::
        :hide:

        >>> if 'ssl' in PROTOCOL:
        ...     from odoorpc import rpc
        ...     cnt = rpc.ConnectorJSONRPCSSL(HOST, port=PORT)
    """
    def __init__(self, host, port=8069, timeout=120, version=None,
                 deserialize=True):
        super(ConnectorJSONRPCSSL, self).__init__(host, port, timeout, version)
        self._proxy_json, self._proxy_http = self._get_proxies()

    @property
    def ssl(self):
        return True


PROTOCOLS = {
    'jsonrpc': ConnectorJSONRPC,
    'jsonrpc+ssl': ConnectorJSONRPCSSL,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
