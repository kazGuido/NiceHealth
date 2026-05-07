"""Generate a simple PDF summary for a health measurement (French labels)."""
from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .models import HealthMeasurement


def _pick_record(data: Dict[str, Any]) -> Dict[str, Any]:
    if not data:
        return {}
    datas = data.get("datas")
    if isinstance(datas, list) and datas and isinstance(datas[0], dict):
        return datas[0]
    return data


def build_measurement_pdf(measurement: HealthMeasurement) -> bytes:
    """Return PDF bytes for one measurement."""
    data = measurement.measurement_data or {}
    rec = _pick_record(dict(data))
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
    styles = getSampleStyleSheet()
    story = []

    title = styles["Title"]
    body = styles["BodyText"]

    story.append(Paragraph("Rapport de mesure — NiceHealth", title))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f"<b>Date:</b> {measurement.created_at.strftime('%d/%m/%Y %H:%M UTC') if measurement.created_at else '—'}",
        body,
    ))
    dev = measurement.device_id or rec.get("deviceNo") or rec.get("deviceID") or "—"
    story.append(Paragraph(f"<b>Appareil:</b> {dev}", body))
    pid = measurement.patient_id or rec.get("patientId") or rec.get("patient_id")
    if pid:
        story.append(Paragraph(f"<b>Patient / ID:</b> {pid}", body))

    rows = [["Champ", "Valeur"]]
    keys = [
        ("weight", "Poids (kg)", ["weight", "Weight"]),
        ("height", "Taille (cm)", ["height", "Height"]),
        ("bmi", "IMC", ["bmi", "BMI", "imc", "IMC"]),
        ("fatRate", "Masse grasse %", ["fatRate", "fat"]),
        ("heartRate", "Fréquence cardiaque", ["heartRate", "pulse"]),
        ("systolic", "Tension systolique", ["highPressure", "systolic"]),
        ("diastolic", "Tension diastolique", ["lowPressure", "diastolic"]),
    ]
    for _, label, aliases in keys:
        val: Optional[Any] = None
        for a in aliases:
            if a in rec and rec[a] not in (None, ""):
                val = rec[a]
                break
        if val is not None:
            rows.append([label, str(val)])

    if len(rows) > 1:
        t = Table(rows, colWidths=[6 * cm, 10 * cm])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(Spacer(1, 0.4 * cm))
        story.append(t)

    story.append(Spacer(1, 1 * cm))
    story.append(
        Paragraph(
            "<i>Document généré automatiquement. Pour le détail complet, consultez le rapport dans l’application.</i>",
            styles["Normal"],
        )
    )

    doc.build(story)
    return buf.getvalue()
