# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2012 OpenStack Foundation
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""
Tests for Consoleauth Code.

"""

import mox
from nova.consoleauth import manager
from nova import context
from nova.openstack.common import timeutils
from nova import test


class ConsoleauthTestCase(test.TestCase):
    """Test Case for consoleauth."""

    def setUp(self):
        super(ConsoleauthTestCase, self).setUp()
        self.manager = manager.ConsoleAuthManager()
        self.context = context.get_admin_context()

    def test_tokens_expire(self):
        # Test that tokens expire correctly.
        self.useFixture(test.TimeOverride())
        token = u'mytok'
        self.flags(console_token_ttl=1)

        self._stub_validate_console_port(True)

        self.manager.authorize_console(self.context, token, 'novnc',
                                         '127.0.0.1', '8080', 'host',
                                         'instance')
        self.assertTrue(self.manager.check_token(self.context, token))
        timeutils.advance_time_seconds(1)
        self.assertFalse(self.manager.check_token(self.context, token))

    def _stub_validate_console_port(self, result):
        def fake_validate_console_port(ctxt, instance, port, console_type):
            return result

        self.stubs.Set(self.manager.compute_rpcapi,
                       'validate_console_port',
                       fake_validate_console_port)

    def test_multiple_tokens_for_instance(self):
        tokens = [u"token" + str(i) for i in xrange(10)]
        instance = u"12345"

        self._stub_validate_console_port(True)

        for token in tokens:
            self.manager.authorize_console(self.context, token, 'novnc',
                                          '127.0.0.1', '8080', 'host',
                                          instance)

        for token in tokens:
            self.assertTrue(self.manager.check_token(self.context, token))

    def test_delete_tokens_for_instance(self):
        instance = u"12345"
        tokens = [u"token" + str(i) for i in xrange(10)]
        for token in tokens:
            self.manager.authorize_console(self.context, token, 'novnc',
                                          '127.0.0.1', '8080', 'host',
                                          instance)
        self.manager.delete_tokens_for_instance(self.context, instance)
        stored_tokens = self.manager._get_tokens_for_instance(instance)

        self.assertEqual(len(stored_tokens), 0)

        for token in tokens:
            self.assertFalse(self.manager.check_token(self.context, token))

    def test_wrong_token_has_port(self):
        token = u'mytok'

        self._stub_validate_console_port(False)

        self.manager.authorize_console(self.context, token, 'novnc',
                                        '127.0.0.1', '8080', 'host',
                                        instance_uuid=u'instance')
        self.assertFalse(self.manager.check_token(self.context, token))

    def test_console_no_instance_uuid(self):
        self.manager.authorize_console(self.context, u"token", 'novnc',
                                        '127.0.0.1', '8080', 'host',
                                        instance_uuid=None)
        self.assertFalse(self.manager.check_token(self.context, u"token"))


class ControlauthMemcacheEncodingTestCase(test.TestCase):
    def setUp(self):
        super(ControlauthMemcacheEncodingTestCase, self).setUp()
        self.manager = manager.ConsoleAuthManager()
        self.context = context.get_admin_context()
        self.u_token = u"token"
        self.u_instance = u"instance"

    def test_authorize_console_encoding(self):
        self.mox.StubOutWithMock(self.manager.mc, "set")
        self.mox.StubOutWithMock(self.manager.mc, "get")
        self.manager.mc.set(mox.IsA(str), mox.IgnoreArg(), mox.IgnoreArg()
                           ).AndReturn(True)
        self.manager.mc.get(mox.IsA(str)).AndReturn(None)
        self.manager.mc.set(mox.IsA(str), mox.IgnoreArg()).AndReturn(True)

        self.mox.ReplayAll()

        self.manager.authorize_console(self.context, self.u_token, 'novnc',
                                       '127.0.0.1', '8080', 'host',
                                       self.u_instance)

    def test_check_token_encoding(self):
        self.mox.StubOutWithMock(self.manager.mc, "get")
        self.manager.mc.get(mox.IsA(str)).AndReturn(None)

        self.mox.ReplayAll()

        self.manager.check_token(self.context, self.u_token)

    def test_delete_tokens_for_instance_encoding(self):
        self.mox.StubOutWithMock(self.manager.mc, "delete")
        self.mox.StubOutWithMock(self.manager.mc, "get")
        self.manager.mc.get(mox.IsA(str)).AndReturn('["token"]')
        self.manager.mc.delete(mox.IsA(str)).AndReturn(True)
        self.manager.mc.delete(mox.IsA(str)).AndReturn(True)

        self.mox.ReplayAll()

        self.manager.delete_tokens_for_instance(self.context, self.u_instance)


class CellsConsoleauthTestCase(ConsoleauthTestCase):
    """Test Case for consoleauth w/ cells enabled."""

    def setUp(self):
        super(CellsConsoleauthTestCase, self).setUp()
        self.flags(enable=True, group='cells')

    def _stub_validate_console_port(self, result):
        def fake_validate_console_port(ctxt, instance_uuid, console_port,
                                       console_type):
            return result

        self.stubs.Set(self.manager.cells_rpcapi,
                       'validate_console_port',
                       fake_validate_console_port)
