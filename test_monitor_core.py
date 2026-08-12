import tempfile
import unittest
from datetime import date
from pathlib import Path

from monitor_core import (
    CoverageResult,
    SeatResult,
    SnapshotStore,
    SubscriberStore,
    adjacent_target_pairs,
    upcoming_watch_dates,
    screening_key,
)
from subscription_bot import command_receiver_enabled


class MonitorCoreTests(unittest.TestCase):
    def test_only_primary_receives_telegram_commands(self):
        self.assertTrue(command_receiver_enabled("primary"))
        self.assertFalse(command_receiver_enabled("standby"))
        with self.assertRaises(ValueError):
            command_receiver_enabled("anything-else")

    def test_dynamic_dates_include_three_weekends_and_exception(self):
        dates = upcoming_watch_dates(date(2026, 8, 12), extra_dates=[date(2026, 8, 17)])
        self.assertEqual(
            [(x.ymd, x.start_hour) for x in dates],
            [
                ("20260814", 19), ("20260815", 0), ("20260816", 0),
                ("20260817", 0),
                ("20260821", 19), ("20260822", 0), ("20260823", 0),
                ("20260828", 19), ("20260829", 0), ("20260830", 0),
            ],
        )

    def test_current_friday_and_today_exception_are_included(self):
        dates = upcoming_watch_dates(date(2026, 8, 14), extra_dates=[date(2026, 8, 14)])
        self.assertIn(("20260814", 19), [(x.ymd, x.start_hour) for x in dates])

    def test_adjacent_pairs_only_in_target_rows(self):
        self.assertEqual(
            adjacent_target_pairs(["F15", "G14", "G15", "H20", "H22", "J8", "J9"]),
            ["G14·G15", "J8·J9"],
        )

    def test_adjacent_pairs_use_fixed_auditorium_center(self):
        layout = [f"G{x}" for x in range(1, 36)]
        available = ["G1", "G2", "G17", "G18", "G34", "G35"]
        self.assertEqual(
            adjacent_target_pairs(available, all_seats=layout, center_radius=15),
            ["G17·G18"],
        )

    def test_coverage_must_be_complete_before_final_result(self):
        expected = frozenset({"0013|20260814|21:30", "0199|20260814|19:30"})
        partial = CoverageResult(expected, frozenset({"0199|20260814|19:30"}))
        self.assertFalse(partial.complete)
        self.assertEqual(partial.missing, ("0013|20260814|21:30",))
        self.assertTrue(CoverageResult(expected, expected).complete)

    def test_screening_key_rejects_unverified_scope(self):
        self.assertEqual(screening_key("0013", "20260814", "21:30"), "0013|20260814|21:30")
        with self.assertRaises(ValueError):
            screening_key("9999", "20260814", "21:30")

    def test_snapshot_reports_only_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(Path(directory) / "state.json")
            first = [SeatResult("용산", "20260821", "21:00", ("G14", "G15"))]
            self.assertTrue(store.compare_and_save(first))
            self.assertEqual(store.compare_and_save(first), {})
            second = [SeatResult("용산", "20260821", "21:00", ("G15",))]
            self.assertTrue(store.compare_and_save(second))

    def test_subscriber_add_remove_and_migration_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SubscriberStore(Path(directory) / "subscribers.json", "100")
            self.assertEqual(store.load(), {"100"})
            self.assertTrue(store.add("200"))
            self.assertFalse(store.add("200"))
            self.assertEqual(store.load(), {"100", "200"})
            self.assertTrue(store.remove("100"))
            self.assertEqual(store.load(), {"200"})


if __name__ == "__main__":
    unittest.main()
