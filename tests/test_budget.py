import unittest

from budget import evaluate


def buckets(failures, total=1000):
    return [
        {"minute": index, "total": total, "failed": failures(index)}
        for index in range(360)
    ]


class BudgetTest(unittest.TestCase):
    def test_both_windows_page(self):
        result = evaluate(buckets(lambda minute: 20 if minute >= 300 else 0), 0.999)
        self.assertEqual(result["decision"], "page")
        self.assertAlmostEqual(result["burn_rates"]["5m"], 20)

    def test_persistent_lower_burn_creates_ticket(self):
        self.assertEqual(evaluate(buckets(lambda _: 7), 0.999)["decision"], "ticket")

    def test_short_spike_alone_stays_healthy(self):
        self.assertEqual(evaluate(buckets(lambda minute: 20 if minute >= 355 else 0), 0.999)["decision"], "healthy")

    def test_no_traffic_is_insufficient_data(self):
        self.assertEqual(evaluate(buckets(lambda _: 0, total=0), 0.999)["decision"], "insufficient_data")

    def test_missing_bucket_is_rejected(self):
        samples = buckets(lambda _: 0)
        samples[-1]["minute"] += 1
        with self.assertRaises(ValueError):
            evaluate(samples, 0.999)

    def test_ticket_boundary_is_inclusive(self):
        self.assertEqual(evaluate(buckets(lambda _: 6), 0.999)["decision"], "ticket")
