import unittest2
import check_graphite

class CheckGraphiteDataEvaluationTests(unittest2.TestCase):

    def test_no_exit_without_nones(self):
        self.assertEquals(check_graphite.check_max_none_values([5, 10, 20], 50, False),None)

    def test_no_exit_some_nones(self):
        self.assertEquals(check_graphite.check_max_none_values([5, 10, "None"], 50, False),None)

    def test_no_exit_without_values(self):
        self.assertEquals(check_graphite.check_max_none_values([], 5, False),None)

    def test_exit_unknown_with_nones(self):
        with self.assertRaises(SystemExit) as cm:
            check_graphite.check_max_none_values(["None", "None", 1, "None"], 50, False)
        self.assertEqual(cm.exception, 3)

    def test_exit_critical_with_nones_if_configured(self):
        with self.assertRaises(SystemExit) as cm:
            check_graphite.check_max_none_values(["None", "None", 1, "None"], 50, True)
        self.assertEqual(cm.exception, 2)