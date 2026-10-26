from __future__ import annotations

from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.time import utc_now_iso
from app.persistence.repositories import AnalysisRecord

DISCLAIMER = (
    "RESEARCH AND EDUCATION ONLY. This report describes wild-type structural context and coarse "
    "physicochemical descriptors. It does not model the mutant structure, does not establish changed "
    "contacts or stability, and is not a pathogenicity or clinical prediction."
)


def _p(text: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(text)), style)


def _table(rows: list[list[Any]], widths: list[float], header: bool = True) -> Table:
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")))
        commands.append(("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"))
    table.setStyle(TableStyle(commands))
    return table


def _footer(canvas: Any, doc: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(18 * mm, 10 * mm, "Mutation Domino - wild-type structural context - research use only")
    canvas.drawRightString(192 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf_report(record: AnalysisRecord) -> bytes:
    result = record.result
    protein = result.get("protein", {})
    structure = result.get("structure", {})
    mapping = result.get("mapping", {})
    variant = result.get("variant", {})
    confidence = result.get("confidence", {})
    properties = result.get("properties", {})
    neighborhood = result.get("neighborhood", {})
    interpretation = result.get("interpretation", {})
    provenance = result.get("provenance", {})

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title=f"Mutation Domino report {record.id}",
        author="Mutation Domino",
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle("BodyMD", parent=styles["BodyText"], fontSize=9, leading=12, alignment=TA_LEFT)
    small = ParagraphStyle(
        "SmallMD", parent=body, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#334155")
    )
    h1 = ParagraphStyle("H1MD", parent=styles["Title"], fontSize=17, leading=21, spaceAfter=4)
    h2 = ParagraphStyle(
        "H2MD", parent=styles["Heading2"], fontSize=11.5, leading=14, spaceBefore=8, spaceAfter=3
    )
    caution = ParagraphStyle(
        "CautionMD",
        parent=body,
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#7c2d12"),
        backColor=colors.HexColor("#fff7ed"),
        borderColor=colors.HexColor("#fdba74"),
        borderWidth=0.6,
        borderPadding=5,
        spaceAfter=8,
    )
    story: list[Any] = []
    story.append(_p("Mutation Domino", h1))
    story.append(_p("Confidence-aware missense-variant structural-context report", body))
    story.append(_p(f"Analysis {record.id} - generated {record.created_at} - export {utc_now_iso()}", small))
    story.append(Spacer(1, 4))
    story.append(_p(DISCLAIMER, caution))

    story.append(_p("1. Input and mapping", h2))
    input_rows = [
        ["Field", "Value"],
        ["UniProt accession", record.accession],
        ["Protein", protein.get("name", "")],
        ["Organism", protein.get("organism", "")],
        ["Substitution", variant.get("normalized", record.variant)],
        ["Canonical position", mapping.get("canonical_position", "")],
        [
            "Structure chain / residue",
            f"{mapping.get('structure_chain', '')} / {mapping.get('structure_residue_id', '')}",
        ],
        ["Residue", f"{mapping.get('residue_name', '')} ({mapping.get('residue_three_letter', '')})"],
        ["Mapping status", mapping.get("mapping_status", "")],
        [
            "Alignment coverage / identity",
            f"{mapping.get('alignment', {}).get('coverage', '')} / "
            f"{mapping.get('alignment', {}).get('identities', '')} of "
            f"{mapping.get('alignment', {}).get('aligned_columns', '')} aligned columns",
        ],
    ]
    story.append(_table([[_p(cell, small) for cell in row] for row in input_rows], [52 * mm, 122 * mm]))

    story.append(_p("2. Data provenance", h2))
    provenance_rows = [
        ["Field", "Value"],
        ["Analysis mode", provenance.get("mode", "")],
        ["Protein source", (provenance.get("protein_source") or {}).get("name", "")],
        ["Protein URL", (provenance.get("protein_source") or {}).get("url", "")],
        ["Protein retrieved", (provenance.get("protein_source") or {}).get("retrieved_at", "")],
        ["Structure source", structure.get("source", "")],
        ["Structure URL", structure.get("url", "")],
        ["Structure model version", structure.get("model_version", "")],
        ["Structure chain", structure.get("chain", "")],
        ["Structure retrieved", structure.get("retrieved_at", "")],
        ["SHA-256", structure.get("checksum_sha256", "")],
        ["Predicted model", "yes" if structure.get("is_predicted") else "no"],
        ["Algorithm version", result.get("algorithm_version", "")],
        ["Schema version", result.get("schema_version", "")],
        ["Parameters", str(provenance.get("parameters", {}))],
    ]
    story.append(_table([[_p(cell, small) for cell in row] for row in provenance_rows], [52 * mm, 122 * mm]))

    story.append(_p("3. Confidence", h2))
    story.append(_p(confidence.get("semantics", ""), body))
    confidence_rows = [
        ["Field", "Value"],
        ["Source", confidence.get("source", "")],
        ["Availability", confidence.get("availability", "")],
        ["Per-residue value", confidence.get("per_residue_value", "not available")],
        ["Band", (confidence.get("band") or {}).get("label", "not applicable")],
        ["Note", confidence.get("note", "")],
    ]
    story.append(_table([[_p(cell, small) for cell in row] for row in confidence_rows], [52 * mm, 122 * mm]))

    story.append(_p("4. Residue chemistry (coarse descriptors)", h2))
    wt = properties.get("wild_type", {})
    mutant = properties.get("mutant", {})
    deltas = properties.get("deltas", {})
    property_rows = [
        ["Descriptor", "Wild type", "Mutant", "Delta"],
        [
            "Category",
            wt.get("category", ""),
            mutant.get("category", ""),
            "changed" if deltas.get("category_changed") else "same",
        ],
        [
            "Charge class",
            wt.get("charge_class", ""),
            mutant.get("charge_class", ""),
            "changed" if deltas.get("charge_class_changed") else "same",
        ],
        [
            "Aromatic",
            wt.get("aromatic", ""),
            mutant.get("aromatic", ""),
            "changed" if deltas.get("aromatic_changed") else "same",
        ],
        [
            "Hydropathy (Kyte-Doolittle)",
            wt.get("hydropathy", ""),
            mutant.get("hydropathy", ""),
            deltas.get("hydropathy", ""),
        ],
        [
            "Residue mass (Da)",
            wt.get("residue_mass_da", ""),
            mutant.get("residue_mass_da", ""),
            deltas.get("residue_mass_da", ""),
        ],
        [
            "Side-chain heavy atoms",
            wt.get("sidechain_heavy_atoms", ""),
            mutant.get("sidechain_heavy_atoms", ""),
            deltas.get("sidechain_heavy_atoms", ""),
        ],
    ]
    story.append(
        _table(
            [[_p(cell, small) for cell in row] for row in property_rows], [52 * mm, 40 * mm, 40 * mm, 42 * mm]
        )
    )
    story.append(_p((properties.get("table") or {}).get("source", ""), small))

    story.append(_p("5. Wild-type structural neighborhood", h2))
    for observation in interpretation.get("observations", []):
        story.append(_p(f"- {observation}", body))
    ca = neighborhood.get("ca_neighbors", {})
    contacts = neighborhood.get("heavy_atom_contacts", {})
    story.append(
        _p(
            f"CA neighbors within {ca.get('radius_angstrom', '')} Angstrom: {ca.get('count', 0)}. "
            f"Heavy-atom contacts within {contacts.get('radius_angstrom', '')} Angstrom: "
            f"{contacts.get('count', 0)}.",
            body,
        )
    )
    story.append(_p("Closest CA neighbors (max 12 shown, closest first)", h2))
    story.append(_neighbor_table(ca.get("rows", []), small, "CA distance (A)"))
    story.append(_p("Closest heavy-atom contacts (max 12 shown, closest first)", h2))
    story.append(_neighbor_table(contacts.get("rows", []), small, "Min heavy-atom distance (A)"))

    story.append(_p("6. Interpretation and cautions", h2))
    for descriptor in interpretation.get("descriptors", []):
        story.append(_p(f"- {descriptor}", body))
    story.append(Spacer(1, 3))
    for item in interpretation.get("cautions", []):
        story.append(_p(f"CAUTION: {item}", body))
    if record.warnings:
        story.append(_p("Warnings from data retrieval or analysis", h2))
        for warning in record.warnings:
            story.append(_p(f"- {warning}", body))
    story.append(Spacer(1, 6))
    story.append(
        _p(
            "Method summary: canonical UniProt sequence was aligned globally to the selected structure "
            "chain; the requested resident was required to map uniquely with matching residue identity. "
            "Distances "
            "were computed on the supplied wild-type coordinates using heavy (non-hydrogen) atoms for "
            "contacts. No mutant coordinates were generated.",
            small,
        )
    )
    story.append(
        _p(
            "Cite data sources: UniProt (https://www.uniprot.org) and AlphaFold Protein Structure Database "
            "(https://alphafold.ebi.ac.uk). Model and license terms remain those of the original providers.",
            small,
        )
    )
    if history := result.get("protein", {}).get("gene"):
        story.append(_p(f"Gene: {history}", small))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _neighbor_table(rows: list[dict[str, Any]], style: ParagraphStyle, distance_label: str) -> Table:
    data: list[list[Any]] = [
        ["Residue", "Canonical", "One-letter", "Category", distance_label],
    ]
    for row in rows[:12]:
        data.append(
            [
                f"{row.get('resname', '')}{row.get('residue_id', '')}",
                row.get("canonical_position", "-"),
                row.get("one_letter", ""),
                (row.get("properties") or {}).get("category", ""),
                row.get("distance_angstrom", ""),
            ]
        )
    if len(data) == 1:
        data.append(["No entries", "-", "-", "-", "-"])
    return _table(
        [[_p(cell, style) for cell in row] for row in data], [45 * mm, 25 * mm, 20 * mm, 32 * mm, 52 * mm]
    )
