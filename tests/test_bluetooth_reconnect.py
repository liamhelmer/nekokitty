from __future__ import annotations

import unittest

from neko.bluetooth_reconnect import (
    configured_addresses,
    ensure_speaker,
    info_is_connected,
)


PRIMARY = "AA:BB:CC:DD:EE:01"
BACKUP = "AA:BB:CC:DD:EE:02"


class FakeBackend:
    def __init__(self, connected: set[str], available: set[str]) -> None:
        self.connected_addresses = connected
        self.available = available
        self.attempts: list[str] = []

    def connected(self, address: str) -> bool:
        return address in self.connected_addresses

    def connect(self, address: str) -> bool:
        self.attempts.append(address)
        if address not in self.available:
            return False
        self.connected_addresses.add(address)
        return True


class BluetoothReconnectTests(unittest.TestCase):
    def test_configuration_preserves_preference_order(self) -> None:
        self.assertEqual(
            configured_addresses(f" {PRIMARY.lower()}, {BACKUP} "),
            (PRIMARY, BACKUP),
        )
        with self.assertRaises(ValueError):
            configured_addresses("")
        with self.assertRaises(ValueError):
            configured_addresses("not-an-address")

    def test_connected_parser_is_exact(self) -> None:
        self.assertTrue(info_is_connected("Name: Speaker\n\tConnected: yes\n"))
        self.assertFalse(info_is_connected("Connected: no\n"))

    def test_existing_backup_is_not_replaced(self) -> None:
        backend = FakeBackend({BACKUP}, {PRIMARY, BACKUP})
        self.assertEqual(
            ensure_speaker((PRIMARY, BACKUP), backend),  # type: ignore[arg-type]
            ("connected", 1),
        )
        self.assertEqual(backend.attempts, [])

    def test_primary_is_attempted_before_backup(self) -> None:
        backend = FakeBackend(set(), {BACKUP})
        self.assertEqual(
            ensure_speaker((PRIMARY, BACKUP), backend),  # type: ignore[arg-type]
            ("reconnected", 1),
        )
        self.assertEqual(backend.attempts, [PRIMARY, BACKUP])


if __name__ == "__main__":
    unittest.main()
