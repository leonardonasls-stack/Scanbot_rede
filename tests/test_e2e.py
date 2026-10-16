import asyncio
import os
import unittest
from backend.core.scanner import NetworkScanner
from backend.services.report_service import export_to_csv, export_to_json, get_reports_dir, write_scan_log_txt
from tests.mock_control_id_server import MockServerThread


class TestEndToEndScan(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_server = MockServerThread("127.0.0.1", 8089)
        cls.mock_server.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_server.stop()

    def test_full_scan_and_export_lifecycle(self):
        async def run_lifecycle():
            found_devices = []
            progress_count = [0]

            def on_progress(scanned, total, ip):
                progress_count[0] = scanned

            def on_device(dev):
                found_devices.append(dev)

            scanner = NetworkScanner(
                cidr="127.0.0.0/30",
                concurrency=5,
                port=8089,
                timeout_sec=1.0,
                on_progress=on_progress,
                on_device_found=on_device
            )

            summary = await scanner.scan()

            # Validação do sumário
            self.assertEqual(summary.network_target, "127.0.0.0/30")
            self.assertEqual(summary.total_scanned, 2)
            self.assertGreaterEqual(summary.total_found, 1)

            # Exportação de relatórios
            csv_path = export_to_csv(summary)
            json_path = export_to_json(summary)
            txt_path = write_scan_log_txt(summary)

            self.assertTrue(os.path.exists(csv_path))
            self.assertTrue(os.path.exists(json_path))
            self.assertTrue(os.path.exists(txt_path))

            # Validação do conteúdo do CSV
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
                self.assertIn("RELATORIO DE VARREDURA", content)
                self.assertIn("100200300400500", content)
                self.assertIn("iDFace", content)

            # Validação do conteúdo do JSON
            with open(json_path, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn('"model": "iDFace"', content)
                self.assertIn('"serial_number": "100200300400500"', content)

            # Validação do conteúdo do TXT Log
            with open(txt_path, "r", encoding="utf-8") as f:
                txt_content = f.read()
                self.assertIn("LOG DE AUDITORIA E COLETA DE EQUIPAMENTOS", txt_content)
                self.assertIn("100200300400500", txt_content)
                self.assertIn("127.0.0.1", txt_content)

        asyncio.run(run_lifecycle())


if __name__ == "__main__":
    unittest.main()
