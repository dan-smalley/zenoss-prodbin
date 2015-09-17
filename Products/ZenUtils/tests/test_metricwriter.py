##############################################################################
#
# Copyright (C) Zenoss, Inc. 2015, all rights reserved.
#
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
#
##############################################################################

"""Tests for Products.ZenUtils.metricwriter module."""

import unittest

from Products.ZenUtils.metricwriter import DerivativeTracker


class TestDerivativeTracker(unittest.TestCase):

    """Test DerivativeTracker class."""

    def test_derivative(self):
        tracker = DerivativeTracker()

        cases = [
            # COUNTER or DERIVE with minimum of 0. Most common case.
            ('counter',   0,  0,   0, 'U', None),
            ('counter',   0, 10,   0, 'U',  0.0),
            ('counter',  20, 20,   0, 'U',  2.0),
            ('counter',   0, 30,   0, 'U', None),
            ('counter',  55, 40,   0, 'U',  5.5),
            ('counter',  55, 40,   0, 'U', None),

            # DERIVE with no minimum or maximum. Rare aside from mistakes.
            ('derive',    0,  0, 'U', 'U', None),
            ('derive',    0, 10, 'U', 'U',  0.0),
            ('derive',   20, 20, 'U', 'U',  2.0),
            ('derive',    0, 30, 'U', 'U', -2.0),
            ('derive',   55, 40, 'U', 'U',  5.5),
            ('derive',   55, 40, 'U', 'U', None),

            # DERIVE with maximum of 0. Never seen it, but test anyway.
            ('reverse',   0,  0, 'U',   0, None),
            ('reverse',   0, 10, 'U',   0,  0.0),
            ('reverse', -20, 20, 'U',   0, -2.0),
            ('reverse',   0, 30, 'U',   0, None),
            ('reverse', -55, 40, 'U',   0, -5.5),
            ('reverse', -55, 40, 'U',   0, None),
            ]

        for name, v, t, minval, maxval, expected_result in cases:
            result = tracker.derivative(name, (v, t), min=minval, max=maxval)
            self.assertEqual(
                result,
                expected_result,
                "{}(v={}, t={}, min={}, max={}) is {} instead of {}".format(
                    name, v, t, minval, maxval, result, expected_result))


def test_suite():
    return unittest.TestSuite((unittest.makeSuite(TestDerivativeTracker),))


if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
