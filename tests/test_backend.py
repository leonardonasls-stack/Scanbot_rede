import asyncio
import os
import unittest
from datetime import datetime

from backend.models.device import ControlIdDevice, ScanSummary
from backend.core.arp_helper import get_mac_for_ip
from backend.core.network_utils import (
    get_local_ip,
    get_local_network_info,
    validate_cidr,
    get_hosts_in_cidr,
)
from backend.core.detector import probe_control_id, login_control_id, _extract_model
from backend.core.scanner import NetworkScanner
from backend.services.report_service import export_to_csv, export_to_json
from tests.mock_control_id_server import MockServerThread
import httpx


class TestBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_server = MockServerThread("127.0.0.1", 8089)
        cls.mock_server.start()

    @classmethod
    def tearDownClass(cls):
        cls.mock_server.stop()

    def test_tc01_arp_local_or_gateway(self):
        # Loopback ou local deve retornar string segura sem exceptions
        mac = get_mac_for_ip("127.0.0.1")
        self.assertIn(mac, ["N/D", "00:00:00:00:00:00"])

    def test_tc03_tc04_network_utils(self):
        ip, net = get_local_network_info()
        self.assertTrue(validate_cidr(net))
        self.assertTrue(validate_cidr("192.168.1.0/24"))
        self.assertFalse(validate_cidr("invalido/99"))
        self.assertFalse(validate_cidr(""))

        hosts = get_hosts_in_cidr("192.168.1.0/30")
        self.assertEqual(len(hosts), 2)
        self.assertEqual(hosts, ["192.168.1.1", "192.168.1.2"])

    def test_tc05_detector_probe_idface(self):
        async def run_probe():
            async with httpx.AsyncClient() as client:
                device = await probe_control_id(client, "127.0.0.1", port=8089)
                self.assertIsNotNone(device)
                self.assertEqual(device.serial_number, "100200300400500")
                self.assertEqual(device.model, "iDFace")
                self.assertEqual(device.firmware_version, "2.4.1")
        asyncio.run(run_probe())

    def test_tc_auth_login_control_id(self):
        async def run_auth_test():
            async with httpx.AsyncClient() as client:
                # 1. Login com credenciais válidas
                session = await login_control_id(client, "127.0.0.1", port=8089, username="admin", password="admin")
                self.assertEqual(session, "mock_valid_session_123")

                # 2. Login com credenciais inválidas
                bad_session = await login_control_id(client, "127.0.0.1", port=8089, username="admin", password="errada")
                self.assertIsNone(bad_session)

                # 3. Probe com dispositivo
                device = await probe_control_id(client, "127.0.0.1", port=8089, username="admin", password="admin")
                self.assertIsNotNone(device)
                self.assertEqual(device.serial_number, "100200300400500")
        asyncio.run(run_auth_test())

    def test_tc11_tc16_tc17_reports_export(self):
        dev1 = ControlIdDevice(
            ip="192.168.0.100",
            mac="AA:BB:CC:DD:EE:FF",
            serial_number="TEST12345",
            model="iDFace",
            firmware_version="2.4.1",
            response_time_ms=12.5,
            timestamp=datetime.now()
        )
        summary = ScanSummary(
            network_target="192.168.0.0/24",
            total_scanned=254,
            total_found=1,
            duration_seconds=15.42,
            devices=[dev1]
        )

        csv_path = export_to_csv(summary)
        self.assertTrue(os.path.exists(csv_path))

        json_path = export_to_json(summary)
        self.assertTrue(os.path.exists(json_path))

        # Confere se os arquivos têm tamanho > 0
        self.assertGreater(os.path.getsize(csv_path), 50)
        self.assertGreater(os.path.getsize(json_path), 50)

    def test_model_extraction_all_models(self):
        # 1. Extração por HTML Title
        self.assertEqual(_extract_model({}, "<title>Control iD - iDFace</title>"), "iDFace")
        self.assertEqual(_extract_model({}, "<title>iDFace Max</title>"), "iDFace Max")
        self.assertEqual(_extract_model({}, "<title>Control iD - iDClass 373</title>"), "iDClass 373")

        # 2. Extração por HTML Body / Scripts / Logos
        self.assertEqual(_extract_model({}, ["<title>Control iD - Login</title><img src='img/idface.png'>"]), "iDFace")
        self.assertEqual(_extract_model({}, ["<title>Login</title><script src='js/idaccess.js'></script>"]), "iDAccess")
        self.assertEqual(_extract_model({}, ["<div>Equipamento iDFlex conectado</div>"]), "iDFlex")

        # 3. Extração por Licença (facial / REP / catraca)
        self.assertEqual(_extract_model({"license": {"type": "facial", "faces": 3000}}, []), "iDFace")
        self.assertEqual(_extract_model({"license": {"type": "rep", "afd": True}}, []), "iDClass")
        self.assertEqual(_extract_model({"license": {"type": "catraca"}}, []), "iDBlock")

        # 4. Extração por Configuração
        self.assertEqual(_extract_model({"_config": {"general": {"device_name": "iDBox"}}}, []), "iDBox")

        # 5. Fallback seguro quando nada específico for detectado
        self.assertEqual(_extract_model({}, ["<title>Control iD - Login</title>"]), "Control iD (Genérico)")
        self.assertEqual(_extract_model({}, []), "Control iD (Genérico)")

        # 6. Identificação de Catraca Facial (iDBlock Facial)
        # 6a. iDFace com flag de catraca ativa (_is_catra)
        self.assertEqual(
            _extract_model({"_is_catra": True}, "<title>Control iD - iDFace</title>"),
            "iDFace (iDBlock Facial)"
        )
        # 6b. iDFace Max com flag de catraca ativa
        self.assertEqual(
            _extract_model({"_is_catra": True}, "<title>iDFace Max</title>"),
            "iDFace Max (iDBlock Facial)"
        )
        # 6c. iDFace com bloco 'catra' nas configurações (/get_configuration.fcgi)
        self.assertEqual(
            _extract_model({
                "model": "iDFace",
                "_config": {"catra": {"gateway": "clockwise", "anti_passback": 1}}
            }, []),
            "iDFace (iDBlock Facial)"
        )
        # 6d. iDFace com nome do dispositivo indicando catraca
        self.assertEqual(
            _extract_model({
                "model": "iDFace",
                "device_name": "Catraca Facial Entrada"
            }, []),
            "iDFace (iDBlock Facial)"
        )

    def test_turnstile_linker_grouping(self):
        from backend.services.turnstile_linker import link_turnstiles_and_readers
        catraca_transporte = ControlIdDevice(
            ip="192.168.1.239",
            model="iDBlock",
            serial_number="0K5210/000015",
            area="Área Padrão, EXTERNA, ENTRADA TRANSPORTE ((Entrada) ENTRADA TRANSPORTE, (Saída) EXTERNA)"
        )
        leitor_transporte_1 = ControlIdDevice(
            ip="192.168.1.151",
            model="iDFace",
            serial_number="0M0200/00C018",
            area="Área Padrão, EXTERNA, ENTRADA TRANSPORTE (Portal)"
        )
        leitor_porta_avulso = ControlIdDevice(
            ip="192.168.1.99",
            model="iDFace",
            serial_number="0M0200/999999",
            area="Portaria Social (Porta 1)"
        )

        devices = [leitor_transporte_1, catraca_transporte, leitor_porta_avulso]
        grouped = link_turnstiles_and_readers(devices)

        # Deve haver 2 grupos principais: a catraca (com 1 filho) e a porta avulsa (sem filhos)
        self.assertEqual(len(grouped), 2)
        parent_turnstile, children = grouped[0]
        self.assertEqual(parent_turnstile.ip, "192.168.1.239")
        self.assertEqual(parent_turnstile.model, "iDBlock Facial")
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].ip, "192.168.1.151")
        self.assertEqual(children[0].parent_turnstile_ip, "192.168.1.239")

        standalone, standalone_children = grouped[1]
        self.assertEqual(standalone.ip, "192.168.1.99")
        self.assertEqual(len(standalone_children), 0)


if __name__ == "__main__":
    unittest.main()
