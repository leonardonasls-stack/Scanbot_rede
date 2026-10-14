import asyncio
import unittest
from backend.core.scanner import NetworkScanner
from tests.mock_control_id_server import MockServerThread


class TestScanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_server = MockServerThread("127.0.0.1", 8089)
        cls.mock_server.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_server.stop()

    def test_scanner_with_mock(self):
        async def run_scan():
            progress_events = []
            found_events = []

            def on_progress(scanned, total, ip):
                progress_events.append((scanned, total, ip))

            def on_found(dev):
                found_events.append(dev)

            # Usa subnet pequena /30 (4 IPs, 2 hosts utilizáveis)
            scanner = NetworkScanner(
                cidr="127.0.0.0/30",
                concurrency=5,
                port=8089,
                timeout_sec=0.5,
                on_progress=on_progress,
                on_device_found=on_found
            )
            summary = await scanner.scan()
            self.assertEqual(summary.network_target, "127.0.0.0/30")
            self.assertEqual(summary.total_scanned, 2)
            self.assertGreaterEqual(len(progress_events), 2)

        asyncio.run(run_scan())

    def test_scanner_cancel(self):
        async def run_cancel():
            scanner = NetworkScanner(
                cidr="192.168.250.0/24",
                concurrency=10,
                port=80,
                timeout_sec=1.5
            )

            async def cancel_soon():
                await asyncio.sleep(0.1)
                scanner.cancel()

            scan_task = asyncio.create_task(scanner.scan())
            cancel_task = asyncio.create_task(cancel_soon())
            summary = await scan_task
            await cancel_task
            # Total escaneado deve ser menor que 254 devido ao cancelamento
            self.assertLess(summary.total_scanned, 254)

        asyncio.run(run_cancel())


if __name__ == "__main__":
    unittest.main()
