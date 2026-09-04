"""Phase 13 prescription PDF generation.

The PDF is a generated representation of the structured prescription
data (V6 section 28). It NEVER includes NID, BCN, or any other
identifier that can be linked to the citizen outside the patient's own
portal. The doctor block lists BM&DC registration number, designation,
and facility — the author doctor is the only professional allowed to
edit and the only one whose precise details need to appear.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import datetime
from html import escape

from reportlab.lib import colors
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


_FORBIDDEN_PATTERNS = (
    re.compile(r"\bnid\b", re.IGNORECASE),
    re.compile(r"\bbirth\s*certificate\b", re.IGNORECASE),
    re.compile(r"\bbcn\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class PrescriptionDoctor:
    """Header details for the author doctor.

    ``bm_dc_registration_no`` is the national medical council number
    printed on the prescription block. ``designation`` and ``facility``
    are the role designation and the facility the prescription was
    rendered at.
    """

    full_name: str
    bm_dc_registration_no: str
    designation: str
    facility_name: str


@dataclass(frozen=True)
class PrescriptionItemView:
    """One structured medicine row in the printed PDF."""

    medicine_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: str | None


@dataclass(frozen=True)
class PrescriptionPdfView:
    """All information needed to render the prescription PDF."""

    prescription_id: str
    visit_date: datetime
    doctor: PrescriptionDoctor
    patient_name: str
    patient_age: str
    serial_label: str
    items: tuple[PrescriptionItemView, ...]
    diagnostic_information: str | None
    medical_advice: str | None
    notes: str | None


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontSize=18,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontSize=11,
            textColor=colors.grey,
            spaceAfter=4,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Heading4"],
            fontSize=12,
            spaceBefore=10,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=10,
            leading=14,
        ),
    }


def _assert_no_forbidden_text(value: str | None, location: str) -> None:
    if not value:
        return
    for pattern in _FORBIDDEN_PATTERNS:
        if pattern.search(value):
            raise ValueError(
                f"Refusing to render forbidden identifier into PDF ({location})"
            )


def _patient_block(styles: dict[str, ParagraphStyle], view: PrescriptionPdfView) -> list:
    rows = [
        ["Patient name", Paragraph(escape(view.patient_name), styles["body"])],
        ["Age / DOB", Paragraph(escape(view.patient_age), styles["body"])],
        ["Serial", Paragraph(escape(view.serial_label), styles["body"])],
        [
            "Visit date",
            Paragraph(view.visit_date.strftime("%Y-%m-%d %H:%M UTC"), styles["body"]),
        ],
    ]
    table = Table(rows, colWidths=[35 * mm, 110 * mm])
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ]
        )
    )
    return [table]


def _doctor_block(styles: dict[str, ParagraphStyle], doctor: PrescriptionDoctor) -> list:
    return [
        Paragraph(f"Dr. {escape(doctor.full_name)}", styles["body"]),
        Paragraph(
            f"BM&amp;DC reg. {escape(doctor.bm_dc_registration_no)}",
            styles["body"],
        ),
        Paragraph(f"Designation: {escape(doctor.designation)}", styles["body"]),
        Paragraph(f"Facility: {escape(doctor.facility_name)}", styles["body"]),
    ]


def _items_table(styles: dict[str, ParagraphStyle], items: tuple[PrescriptionItemView, ...]) -> list:
    header = ["Medicine", "Dosage", "Frequency", "Duration", "Instructions"]
    rows = [header]
    for item in items:
        rows.append(
            [
                Paragraph(escape(item.medicine_name), styles["body"]),
                Paragraph(escape(item.dosage), styles["body"]),
                Paragraph(escape(item.frequency), styles["body"]),
                Paragraph(escape(item.duration), styles["body"]),
                Paragraph(escape(item.instructions or ""), styles["body"]),
            ]
        )
    table = Table(rows, colWidths=[40 * mm, 25 * mm, 25 * mm, 25 * mm, 40 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E0EAF5")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return [table]


def _optional_section(
    styles: dict[str, ParagraphStyle], heading: str, value: str | None
) -> list:
    if not value:
        return []
    return [
        Paragraph(heading, styles["section"]),
        Paragraph(escape(value).replace("\n", "<br/>"), styles["body"]),
    ]


def generate_prescription_pdf_bytes(view: PrescriptionPdfView) -> bytes:
    """Render ``view`` into a PDF byte string.

    Raises ``ValueError`` if any field that gets rendered contains a
    NID/BCN-like identifier — the guard prevents accidental inclusions
    even when the caller hands us a wider view object.
    """

    _assert_no_forbidden_text(view.patient_name, "patient_name")
    _assert_no_forbidden_text(view.patient_age, "patient_age")
    _assert_no_forbidden_text(view.serial_label, "serial_label")
    _assert_no_forbidden_text(view.diagnostic_information, "diagnostic_information")
    _assert_no_forbidden_text(view.medical_advice, "medical_advice")
    _assert_no_forbidden_text(view.notes, "notes")
    for index, item in enumerate(view.items):
        _assert_no_forbidden_text(item.medicine_name, f"items[{index}].medicine_name")
        _assert_no_forbidden_text(item.dosage, f"items[{index}].dosage")
        _assert_no_forbidden_text(item.frequency, f"items[{index}].frequency")
        _assert_no_forbidden_text(item.duration, f"items[{index}].duration")
        _assert_no_forbidden_text(item.instructions, f"items[{index}].instructions")

    styles = _styles()
    buf = io.BytesIO()
    document = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Prescription {view.prescription_id}",
    )
    story: list = []
    story.append(Paragraph("HealthLink Electronic Prescription", styles["title"]))
    story.append(
        Paragraph(
            f"Prescription id: {escape(view.prescription_id)}",
            styles["subtitle"],
        )
    )
    story.append(Spacer(1, 6))
    story.extend(_doctor_block(styles, view.doctor))
    story.append(Spacer(1, 8))
    story.extend(_patient_block(styles, view))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Medicines", styles["section"]))
    story.extend(_items_table(styles, view.items))
    story.extend(_optional_section(styles, "Diagnostic information", view.diagnostic_information))
    story.extend(_optional_section(styles, "Medical advice", view.medical_advice))
    story.extend(_optional_section(styles, "Notes", view.notes))
    document.build(story)
    return buf.getvalue()


__all__ = [
    "PrescriptionDoctor",
    "PrescriptionItemView",
    "PrescriptionPdfView",
    "generate_prescription_pdf_bytes",
]
