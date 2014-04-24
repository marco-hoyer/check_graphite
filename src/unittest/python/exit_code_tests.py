__author__ = 'mhoyer'

import unittest2
import check_graphite

class CheckGraphiteExitCodeTests(unittest2.TestCase):
    def test_exit_ok(self):
        with self.assertRaises(SystemExit) as cm:
            check_graphite.exit_ok("Test")
        self.assertEqual(cm.exception, 0)

    def test_exit_warning(self):
        with self.assertRaises(SystemExit) as cm:
            check_graphite.exit_warning("Test")
        self.assertEqual(cm.exception, 1)

    def test_exit_critical(self):
        with self.assertRaises(SystemExit) as cm:
            check_graphite.exit_critical("Test")
        self.assertEqual(cm.exception, 2)

    def test_exit_unknown(self):
        with self.assertRaises(SystemExit) as cm:
            check_graphite.exit_unknown("Test")
        self.assertEqual(cm.exception, 3)