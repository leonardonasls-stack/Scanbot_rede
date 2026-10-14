import os
import unittest
from datetime import datetime

from backend.models.device import ControlIdDevice, ScanSummary, DocumentMetadata
from backend.services.document_service import generate_internal_document_pdf


class TestDocumentGeneration(unittest.TestCase):
    def test_pdf_creation_with_metadata(self):
        dev1 = ControlIdDevice(
            ip="192.168.0.50",
            mac="00:1A:2B:3C:4D:5E",
            serial_number="99887766",
            model="iDFace",
            firmware_version="2.4.1",
            area="Recepção Central (Catraca Entrada)",
            response_time_ms=11.2,
            timestamp=datetime.now()
        )
        summary = ScanSummary(
            network_target="192.168.0.0/24",
            total_scanned=254,
            total_found=1,
            duration_seconds=12.5,
            devices=[dev1]
        )
        metadata = DocumentMetadata(
            cliente="Empresa Teste",
            rua="Rua das Flores",
            numero="123",
            bairro="Centro",
            tecnico="João Silva",
            local_equipamento="Portaria 1"
        )

        pdf_path = generate_internal_document_pdf(summary, metadata)
        self.assertTrue(os.path.exists(pdf_path))
        self.assertGreater(os.path.getsize(pdf_path), 500)


if __name__ == "__main__":
    unittest.main()
