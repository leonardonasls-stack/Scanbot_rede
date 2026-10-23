from datetime import datetime
from pathlib import Path
from typing import Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable
)

from backend.models.device import ScanSummary, DocumentMetadata
from backend.services.report_service import get_reports_dir, generate_filename


def generate_internal_document_pdf(
    summary: ScanSummary,
    metadata: DocumentMetadata,
    file_path: Optional[str] = None
) -> str:
    """
    Gera um documento em PDF formatado para uso interno técnico.
    Contém os dados manuais do cliente/cabeçalho e a listagem de todos os equipamentos
    (incluindo todos os iDFaces e outros dispositivos Control iD encontrados).
    Retorna o caminho absoluto do arquivo PDF gerado.
    """
    reports_dir = get_reports_dir()
    if not file_path:
        safe_client = "".join(c for c in metadata.cliente if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
        prefix = f"documento_interno_{safe_client}" if safe_client else "documento_interno"
        filename = generate_filename(prefix, "pdf")
        target_path = reports_dir / filename
    else:
        target_path = Path(file_path)

    doc = SimpleDocTemplate(
        str(target_path.resolve()),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Estilos customizados
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#2563EB"),
        spaceAfter=12
    )

    label_style = ParagraphStyle(
        "LabelStyle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155")
    )

    val_style = ParagraphStyle(
        "ValStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0F172A")
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1  # Centralizado
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B")
    )

    table_cell_center = ParagraphStyle(
        "TableCellCenter",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1E293B"),
        alignment=1
    )

    table_cell_mono = ParagraphStyle(
        "TableCellMono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0F172A")
    )

    table_cell_mono_child = ParagraphStyle(
        "TableCellMonoChild",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#0284C7")
    )

    elements = []

    # 1. Cabeçalho Principal
    elements.append(Paragraph("RELATÓRIO TÉCNICO DE EQUIPAMENTOS", title_style))
    elements.append(Paragraph("CONTROLE E INVENTÁRIO TÉCNICO — USO INTERNO", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=14))

    # 2. Informações do Cabeçalho / Dados do Cliente e Técnico
    header_info_data = [
        [
            Paragraph("<b>CLIENTE:</b>", label_style),
            Paragraph(metadata.cliente or "Não informado", val_style),
            Paragraph("<b>DATA/HORA:</b>", label_style),
            Paragraph(metadata.data_emissao.strftime("%d/%m/%Y %H:%M:%S"), val_style),
        ],
        [
            Paragraph("<b>ENDEREÇO:</b>", label_style),
            Paragraph(metadata.endereco_completo, val_style),
            Paragraph("<b>SUB-REDE:</b>", label_style),
            Paragraph(summary.network_target or "N/D", val_style),
        ],
        [
            Paragraph("<b>TÉCNICO:</b>", label_style),
            Paragraph(metadata.tecnico or "Não informado", val_style),
            Paragraph("<b>TOTAL ATIVOS:</b>", label_style),
            Paragraph(f"<b>{len(summary.devices)} equipamento(s)</b>", val_style),
        ],
        [
            Paragraph("<b>LOCAL DO EQUIP.:</b>", label_style),
            Paragraph(metadata.local_equipamento or "Geral", val_style),
            Paragraph("<b>DURAÇÃO SCAN:</b>", label_style),
            Paragraph(f"{summary.duration_seconds:.1f} segundos", val_style),
        ]
    ]

    header_table = Table(header_info_data, colWidths=[100, 220, 80, 122])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 16))

    # 3. Estatísticas / Contadores dos Modelos
    idface_count = sum(1 for d in summary.devices if "face" in d.model.lower())
    idclass_count = sum(1 for d in summary.devices if "class" in d.model.lower())
    outros_count = len(summary.devices) - (idface_count + idclass_count)

    kpi_data = [
        [
            Paragraph("<b>TOTAL GERAL</b>", table_header_style),
            Paragraph("<b>iDFACES</b>", table_header_style),
            Paragraph("<b>iDCLASS / REPs</b>", table_header_style),
            Paragraph("<b>OUTROS EQUIPAMENTOS</b>", table_header_style),
        ],
        [
            Paragraph(f"<font size=12><b>{len(summary.devices)}</b></font>", ParagraphStyle("C1", parent=styles["Normal"], alignment=1, textColor=colors.HexColor("#065F46"))),
            Paragraph(f"<font size=12><b>{idface_count}</b></font>", ParagraphStyle("C2", parent=styles["Normal"], alignment=1, textColor=colors.HexColor("#1E40AF"))),
            Paragraph(f"<font size=12><b>{idclass_count}</b></font>", ParagraphStyle("C3", parent=styles["Normal"], alignment=1, textColor=colors.HexColor("#6B21A8"))),
            Paragraph(f"<font size=12><b>{outros_count}</b></font>", ParagraphStyle("C4", parent=styles["Normal"], alignment=1, textColor=colors.HexColor("#334155"))),
        ]
    ]

    kpi_table = Table(kpi_data, colWidths=[130, 130, 130, 132])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#F1F5F9")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94A3B8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 16))

    # 4. Tabela com todos os Equipamentos (iDFaces e outros)
    elements.append(Paragraph("<b>RELAÇÃO DETALHADA DE EQUIPAMENTOS IDENTIFICADOS</b>", label_style))
    elements.append(Spacer(1, 6))

    from backend.services.turnstile_linker import link_turnstiles_and_readers, clean_display_area
    grouped_pdf = link_turnstiles_and_readers(summary.devices)

    table_data = [
        [
            Paragraph("ITEM", table_header_style),
            Paragraph("IP LOCAL", table_header_style),
            Paragraph("ENDEREÇO MAC", table_header_style),
            Paragraph("NÚMERO DE SÉRIE", table_header_style),
            Paragraph("MODELO / FUNÇÃO", table_header_style),
            Paragraph("ÁREA / LOCAL", table_header_style),
            Paragraph("FIRMWARE", table_header_style),
        ]
    ]

    if not summary.devices:
        table_data.append([
            Paragraph("-", table_cell_center),
            Paragraph("Nenhum equipamento localizado na varredura", table_cell_style),
            Paragraph("-", table_cell_center),
            Paragraph("-", table_cell_center),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_style),
            Paragraph("-", table_cell_center),
        ])
    else:
        parent_counter = 1
        for parent, children in grouped_pdf:
            is_turnstile = "idblock" in parent.model.lower()
            parent_model_str = f"<b>{parent.model}</b>"
            clean_parent_area = clean_display_area(parent)

            table_data.append([
                Paragraph(f"<b>{parent_counter}</b>", table_cell_center),
                Paragraph(f"<b>{parent.ip}</b>", table_cell_mono),
                Paragraph(parent.mac, table_cell_mono),
                Paragraph(parent.serial_number, table_cell_mono),
                Paragraph(parent_model_str, table_cell_style),
                Paragraph(clean_parent_area, table_cell_style),
                Paragraph(parent.firmware_version, table_cell_center),
            ])

            for c_idx, child in enumerate(children, start=1):
                if child.role == "reader_entry":
                    badge_html = "<font color='#059669'><b>[Entrada]</b></font>"
                elif child.role == "reader_exit":
                    badge_html = "<font color='#D97706'><b>[Saída]</b></font>"
                else:
                    badge_html = "<font color='#0284C7'><b>[Vinculado]</b></font>"

                child_model_str = f"{badge_html} {child.model}"
                clean_child_area = clean_display_area(child)

                table_data.append([
                    Paragraph(f"<font color='#64748B'>{parent_counter}.{c_idx}</font>", table_cell_center),
                    Paragraph(f"↳ {child.ip}", table_cell_mono_child),
                    Paragraph(child.mac, table_cell_mono),
                    Paragraph(child.serial_number, table_cell_mono),
                    Paragraph(child_model_str, table_cell_style),
                    Paragraph(clean_child_area, table_cell_style),
                    Paragraph(child.firmware_version, table_cell_center),
                ])

            parent_counter += 1

    # Larguras recalculadas para a página A4 (523pt úteis com margens 36pt):
    # Total = 34 + 92 + 96 + 88 + 98 + 68 + 47 = 523pt
    devices_table = Table(table_data, colWidths=[34, 92, 96, 88, 98, 68, 47])
    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#475569")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]

    # Zebrado nas linhas
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            t_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F8FAFC")))

    devices_table.setStyle(TableStyle(t_style))
    elements.append(devices_table)

    # 5. Rodapé Informativo (Uso Interno)
    elements.append(Spacer(1, 24))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceAfter=8))
    footer_text = (
        "<i>Documento emitido automaticamente pelo SCAN BOT Rede. "
        "Uso estritamente interno para inventário técnico, conferência e manutenção de ativos. "
        "Não requer assinatura de terceiros.</i>"
    )
    elements.append(Paragraph(footer_text, ParagraphStyle("Footer", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#64748B"), alignment=1)))

    # Constrói o PDF
    doc.build(elements)
    return str(target_path.resolve())
