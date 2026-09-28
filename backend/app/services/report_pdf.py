"""
PDF Project Status Report in the format of the FMDQ April 2025 report
(README §31–§38): framed pages with the classification label and logo,
a cover, a contents page, the "Project Status Report" banner and metadata
table, then sections 1–5 with the issue legend and the likelihood / impact
matrices. Executive Assistance Requests are omitted (README §22).

All labels, legend text, matrix text and colours come from the lookup
data (Admin > Reference data); layout constants live here.
"""
from __future__ import annotations
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import List, Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate, NextPageTemplate, PageBreak, Paragraph, Spacer,
    Table, TableStyle, Image, KeepTogether, CondPageBreak,
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.platypus.tableofcontents import TableOfContents

from app.models.report import ProjectStatusReport
from app.services.store import store

ASSETS = Path(__file__).resolve().parent.parent / "assets"
LOGO = ASSETS / "report_logo.png"
LOGO_SMALL = ASSETS / "report_logo_small.png"

PAGE_W, PAGE_H = letter
BORDER_INSET = 26
CONTENT_X = 71
CONTENT_W = PAGE_W - 2 * CONTENT_X

C_BORDER = colors.HexColor("#25375E")
C_BANNER = colors.HexColor("#0B2D5B")
C_RULE = colors.HexColor("#0B3080")
C_HEAD = colors.HexColor("#F2F2F2")
C_GRID = colors.HexColor("#000000")
C_LEGEND_HEAD = colors.HexColor("#A6A6A6")
C_MATRIX_SUB = colors.HexColor("#B4C6E7")
C_MATRIX_HEAD = colors.HexColor("#BFBFBF")


# ---------------------------------------------------------------------------
# Fonts: Calibri (as in the original) when available, else Helvetica.
# ---------------------------------------------------------------------------
_FONT_DIRS = [Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/msttcorefonts"),
              Path("/usr/share/fonts/truetype/crosextra"), Path("/Library/Fonts")]
_CANDIDATES = [("calibri.ttf", "calibrib.ttf", "calibrii.ttf", "calibriz.ttf"),
               ("Carlito-Regular.ttf", "Carlito-Bold.ttf", "Carlito-Italic.ttf", "Carlito-BoldItalic.ttf")]
_fonts: Optional[dict] = None


def _fonts_available() -> dict:
    global _fonts
    if _fonts is not None:
        return _fonts
    for d in _FONT_DIRS:
        for files in _CANDIDATES:
            paths = [d / f for f in files]
            if all(p.exists() for p in paths):
                names = ["RX", "RX-Bold", "RX-Italic", "RX-BoldItalic"]
                for n, p in zip(names, paths):
                    pdfmetrics.registerFont(TTFont(n, str(p)))
                pdfmetrics.registerFontFamily("RX", normal="RX", bold="RX-Bold", italic="RX-Italic", boldItalic="RX-BoldItalic")
                _fonts = {"normal": "RX", "bold": "RX-Bold", "italic": "RX-Italic", "bullet": "\u25aa"}
                return _fonts
    _fonts = {"normal": "Helvetica", "bold": "Helvetica-Bold", "italic": "Helvetica-Oblique", "bullet": "\u2022"}
    return _fonts


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def _us_date(s: Optional[str]) -> Optional[str]:
    """M/D/YYYY as used throughout the original report."""
    try:
        d = date.fromisoformat(s or "")
        return f"{d.month}/{d.day}/{d.year}"
    except ValueError:
        return None


def _period_label(start: str, end: str) -> str:
    """Cover line: 'April 2025', or 'March – April 2025' for a longer period."""
    s, e = date.fromisoformat(start), date.fromisoformat(end)
    if (s.year, s.month) == (e.year, e.month):
        return e.strftime("%B %Y")
    if s.year == e.year:
        return f"{s.strftime('%B')} \u2013 {e.strftime('%B %Y')}"
    return f"{s.strftime('%B %Y')} \u2013 {e.strftime('%B %Y')}"


def _milestone_date(value: Optional[str], placeholders: dict, empty: str) -> str:
    if not value:
        return empty
    if value in placeholders:
        return "Yet to be determined" if value == "TBD" else placeholders[value]
    return _us_date(value) or value


class _Doc(BaseDocTemplate):
    """Registers section headings with the contents page (displayed page = physical - 1)."""

    def afterFlowable(self, flowable):
        toc = getattr(flowable, "_toc", None)
        if toc:
            self.notify("TOCEntry", (toc[0], toc[1], self.page - 1))


def render_pdf(r: ProjectStatusReport) -> bytes:
    f = _fonts_available()
    lookups = store.lookups()
    classification = str(store.setting("report_classification") or "")

    def opt(kind, value) -> dict:
        return next((o for o in lookups.get(kind, []) if o["value"] == str(value)), {})

    def label(kind, value) -> str:
        return opt(kind, value).get("label", str(value)) if value not in (None, "") else "N/A"

    # --- styles -------------------------------------------------------------
    base = ParagraphStyle("base", fontName=f["normal"], fontSize=10.5, leading=13.5)
    small = ParagraphStyle("small", parent=base, fontSize=9, leading=11.5)
    tiny = ParagraphStyle("tiny", parent=base, fontSize=7.5, leading=9)
    tiny_c = ParagraphStyle("tiny_c", parent=tiny, alignment=TA_CENTER)
    head = ParagraphStyle("head", parent=base, fontName=f["bold"])
    head_c = ParagraphStyle("head_c", parent=head, alignment=TA_CENTER)
    center = ParagraphStyle("center", parent=base, alignment=TA_CENTER)
    italic = ParagraphStyle("italic", parent=base, fontName=f["italic"])
    h1 = ParagraphStyle("h1", parent=base, fontName=f["bold"], fontSize=12, leading=15, spaceBefore=14, spaceAfter=10, leftIndent=0)
    cover_title = ParagraphStyle("cover_title", parent=base, fontName=f["bold"], fontSize=24, leading=30, alignment=TA_CENTER)
    cover_sub = ParagraphStyle("cover_sub", parent=base, fontName=f["bold"], fontSize=15, leading=19, alignment=TA_CENTER)
    banner = ParagraphStyle("banner", parent=base, fontName=f["bold"], fontSize=12, textColor=colors.white, alignment=TA_CENTER)
    toc_title = ParagraphStyle("toc_title", parent=base, fontSize=13, leading=16, spaceAfter=18)

    def P(text, style=base) -> Paragraph:
        return Paragraph(escape(str(text)).replace("\n", "<br/>"), style)

    def bullets(lines: List[str], style=small) -> Paragraph:
        items = [l.strip() for l in lines if str(l).strip()] or ["N/A"]
        return Paragraph("<br/><br/>".join(f"{f['bullet']}&nbsp;&nbsp;{escape(i)}" for i in items), style)

    def lines_of(text: str) -> List[str]:
        return [l.strip(" \u2022\u25aa-") for l in (text or "").splitlines() if l.strip()]

    def grid(data, widths, header=True, style_extra=(), repeat=True):
        t = Table(data, colWidths=[CONTENT_W * w for w in widths], repeatRows=1 if (header and repeat) else 0)
        st = [("GRID", (0, 0), (-1, -1), 0.6, C_GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
              ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
              ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]
        if header:
            st.append(("BACKGROUND", (0, 0), (-1, 0), C_HEAD))
        t.setStyle(TableStyle(st + list(style_extra)))
        return t

    def section(num: int, title: str):
        p = Paragraph(f"{num}.&nbsp;&nbsp;&nbsp;{escape(title)}", h1)
        p._toc = (1, f"{num}.\u00a0\u00a0\u00a0\u00a0{title}")
        return p

    m = r.metadata
    placeholders = {o["value"]: o["label"] for o in lookups.get("date_placeholder", [])}

    # --- page decoration ----------------------------------------------------
    def decorate(canvas, doc, cover=False):
        canvas.saveState()
        canvas.setStrokeColor(C_BORDER)
        canvas.setLineWidth(4)
        canvas.rect(BORDER_INSET, BORDER_INSET, PAGE_W - 2 * BORDER_INSET, PAGE_H - 2 * BORDER_INSET)
        if classification:
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.black)
            canvas.drawString(20, PAGE_H - 20, classification)
        if not cover:
            if LOGO_SMALL.exists():
                w = 185
                h = w * 121 / 512
                canvas.drawImage(str(LOGO_SMALL), PAGE_W - BORDER_INSET - w - 8, PAGE_H - BORDER_INSET - h - 6,
                                 width=w, height=h, mask="auto")
            canvas.setFont(f["normal"], 10)
            canvas.drawCentredString(PAGE_W / 2, 44, str(doc.page - 1))
        canvas.restoreState()

    doc = _Doc(BytesIO(), pagesize=letter, title=f"Project Status Report - {m.project_title}",
               author=m.report_author or "", subject=f"{m.project_id} status report")
    body = Frame(CONTENT_X, 70, CONTENT_W, PAGE_H - 70 - 88, id="body", leftPadding=0, rightPadding=0,
                 topPadding=0, bottomPadding=0)
    doc.addPageTemplates([
        PageTemplate("cover", frames=[body], onPage=lambda c, d: decorate(c, d, cover=True)),
        PageTemplate("normal", frames=[body], onPage=decorate),
    ])

    story = []

    # --- cover ----------------------------------------------------------------
    story.append(Spacer(1, 150))
    if LOGO.exists():
        story.append(Image(str(LOGO), width=438, height=438 * 314 / 1326))
    story.append(Spacer(1, 120))
    rule = lambda w: HRFlowable(width=w, thickness=3, color=C_RULE, spaceBefore=0, spaceAfter=0, hAlign="CENTER")
    story += [rule(CONTENT_W), Spacer(1, 12), P("Project Status Report", cover_title), Spacer(1, 10),
              P(m.project_title.upper(), cover_title), Spacer(1, 12), rule(CONTENT_W), Spacer(1, 70),
              rule(178), Spacer(1, 8), P(m.delivery_organisation or "", cover_sub), Spacer(1, 14),
              P(_period_label(m.reporting_period.start_date, m.reporting_period.end_date), cover_sub),
              Spacer(1, 6), rule(178)]
    story += [NextPageTemplate("normal"), PageBreak()]

    # --- contents ---------------------------------------------------------------
    toc = TableOfContents(dotsMinLevel=0)
    toc.levelStyles = [
        ParagraphStyle("toc0", parent=base, fontName=f["bold"], leading=22, leftIndent=0, firstLineIndent=0),
        ParagraphStyle("toc1", parent=base, leading=22, leftIndent=0, firstLineIndent=0),
    ]
    story += [P("Contents", toc_title), toc, PageBreak()]

    # --- banner + metadata ------------------------------------------------------
    title_banner = Table([["", P("Project Status Report", banner)]], colWidths=[6, CONTENT_W + 6], hAlign="RIGHT")
    title_banner.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), C_BORDER), ("BACKGROUND", (1, 0), (1, 0), C_BANNER),
                                      ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                                      ("LEFTPADDING", (0, 0), (0, 0), 0), ("RIGHTPADDING", (0, 0), (0, 0), 0)]))
    title_banner._toc = (0, "Project Status Report")
    period = f"{_us_date(m.reporting_period.start_date)} \u2013 {_us_date(m.reporting_period.end_date)}"
    meta = Table([
        [P("Reporting period:", head), P(period), P("Project title:", head), P(m.project_title)],
        [P("Date of report:", head), P(_us_date(m.date_of_report)), P("Delivery Manager:", head), P(m.delivery_manager or "N/A")],
        [P("Report author:", head), P(m.report_author or "N/A"), P("Executive Sponsor:", head), P(m.executive_sponsor or "N/A")],
    ], colWidths=[CONTENT_W * w for w in (0.20, 0.27, 0.215, 0.315)])
    meta.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, C_GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (0, -1), C_HEAD), ("BACKGROUND", (2, 0), (2, -1), C_HEAD),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 10), ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [title_banner, Spacer(1, 14), meta, Spacer(1, 22)]

    # --- 1. Executive summary -----------------------------------------------------
    def rag_cell(value):
        colour = opt("rag", value).get("report_color")
        return (P("") if colour else P("N/A", center)), colour

    narrative = lines_of(r.executive_summary) or lines_of(r.narrative)
    cells, fills = [], []
    for i, key in enumerate(("schedule", "budget", "issues")):
        comment = getattr(r.rag, f"{key}_comment", "") or ""
        cell, colour = rag_cell(getattr(r.rag, key))
        cells += [bullets(lines_of(comment), small) if comment.strip() else P("N/A", center), cell]
        if colour:
            fills.append(("BACKGROUND", (2 + i * 2, 1), (2 + i * 2, 1), colors.HexColor(colour)))
    exec_table = Table(
        [[P("Narrative Summary of Status", head), P("Schedule:", head_c), P("RAG Status", head_c), P("Budget", head_c),
          P("RAG Status", head_c), P("Issues:", head_c), P("RAG Status", head_c)],
         [bullets(narrative, small)] + cells],
        colWidths=[CONTENT_W * w for w in (0.215, 0.19, 0.115, 0.105, 0.11, 0.155, 0.11)],
    )
    exec_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, C_GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("VALIGN", (0, 1), (0, 1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ] + fills))
    story += [section(1, "Executive Summary"), exec_table, Spacer(1, 12)]

    # --- 2. Milestones ------------------------------------------------------------
    ms_rows = [[P("S/N", head), P("Project Milestones", head), P("Status", head), P("Baseline Completion Date", head),
                P("Expected Completion Date", head), P("Issues Exist (Yes/No)", head)]]
    for i, row in enumerate(r.milestone_status_review, start=1):
        expected = _milestone_date(row.expected_date, placeholders, "N/A")
        if row.actual_date and _us_date(row.actual_date):
            expected = f"{expected}\nActual: {_us_date(row.actual_date)}"
        ms_rows.append([P(i, italic), P(row.label, italic), P(label("milestone_status", row.status)),
                        P(_milestone_date(row.baseline_date, placeholders, "Yet to be determined")),
                        P(expected), P("Yes" if row.has_issues else "No")])
    story += [section(2, "Project Milestone Status Review"),
              grid(ms_rows, (0.115, 0.26, 0.13, 0.14, 0.13, 0.225),
                   style_extra=[("TOPPADDING", (0, 1), (-1, -1), 9), ("BOTTOMPADDING", (0, 1), (-1, -1), 12)]),
              Spacer(1, 12)]

    # --- 3. Planned activities ------------------------------------------------------
    story.append(section(3, "Status of Planned Activities"))
    for title, items in (("Planned accomplishments in this period:", r.planned_activities.accomplishments),
                         ("Planned but not accomplished:", r.planned_activities.not_accomplished),
                         ("Planned actions for the next period:", r.planned_activities.next_period)):
        box = grid([[P(title, head)], [bullets(items, base)]], (1.0,), repeat=False,
                   style_extra=[("BOTTOMPADDING", (0, 1), (-1, 1), 18), ("VALIGN", (0, 1), (-1, 1), "TOP")])
        story += [KeepTogether([box]), Spacer(1, 10)]

    # --- 4. Issues + legend ---------------------------------------------------------
    issue_rows = [[P("S/N", head), P("Priority", head), P("Issue Description", head),
                   P("Impact Summary (Milestone, Schedule Scope, Resources, Space\u2026)", head_c), P("Action Steps", head_c)]]
    for i, iss in enumerate(r.issues, start=1):
        impact = iss.impact_summary + (f"\n({', '.join(iss.impact_areas)})" if iss.impact_areas else "")
        issue_rows.append([P(i), P(label("issue_priority", iss.priority)), P(iss.description or "N/A"),
                           P(impact or "N/A"), P(iss.action_steps or "N/A")])
    if not r.issues:
        issue_rows.append([P("1"), P("N/A"), P("N/A"), P("N/A"), P("N/A")])
    story += [CondPageBreak(160), section(4, "Project Issues Summary"),
              grid(issue_rows, (0.062, 0.107, 0.297, 0.268, 0.266)), Spacer(1, 18)]

    legend_rows = [[Paragraph("<b><i>Legend</i></b>", tiny), ""]]
    legend_style = [("SPAN", (0, 0), (1, 0)), ("BACKGROUND", (0, 0), (1, 0), C_LEGEND_HEAD),
                    ("BOX", (0, 0), (-1, -1), 1.2, C_BANNER), ("INNERGRID", (0, 0), (-1, -1), 1.2, C_BANNER),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    for i, o in enumerate(lookups.get("issue_priority", []), start=1):
        code = f" - {o['code']}" if o.get("code") else ""
        legend_rows.append([P(f"{o['label']}{code}", tiny), Paragraph(f"<i>{escape(o.get('description', ''))}</i>", tiny)])
        if o.get("report_color"):
            legend_style.append(("BACKGROUND", (0, i), (0, i), colors.HexColor(o["report_color"])))
    legend = Table(legend_rows, colWidths=[CONTENT_W * 0.13, CONTENT_W * 0.87])
    legend.setStyle(TableStyle(legend_style))
    story += [KeepTogether([legend]), Spacer(1, 12)]

    # --- 5. Risks + matrices --------------------------------------------------------
    hs = ParagraphStyle("hs", parent=head, fontSize=9, leading=11)
    hs_c = ParagraphStyle("hs_c", parent=hs, alignment=TA_CENTER)
    head, head_c = hs, hs_c   # smaller headers for the eight-column risk table
    risk_rows = [[P("S/N", head), P("Priority", head), P("Probability of Occurrence", head), P("Risk Description", head),
                  P("Impact Summary (Milestone, Schedule Scope, Resources, Space\u2026)", head_c), P("Risk Score", head_c),
                  P("Response Strategy", head_c), P("Status", head_c)]]
    for i, k in enumerate(r.risks, start=1):
        impact = str(k.impact) + (f"\n{k.impact_summary}" if k.impact_summary else "")
        risk_rows.append([P(i, small), P(label("issue_priority", k.priority), small), P(k.probability, small),
                          P(k.description or "N/A", small), P(impact, small), P(k.risk_score, small),
                          P(k.response_strategy or "N/A", small), P(label("risk_status", k.status), small)])
    if not r.risks:
        risk_rows.append([P("1", small)] + [P("N/A", small)] * 7)
    story += [CondPageBreak(160), section(5, "Project Risk Summary"),
              grid(risk_rows, (0.055, 0.1, 0.125, 0.165, 0.135, 0.07, 0.185, 0.165),
                   style_extra=[("VALIGN", (0, 1), (-1, -1), "TOP")])]

    # Likelihood matrix
    lm = [[Paragraph("<b>Likelihood Matrix</b>", ParagraphStyle("lmh", parent=tiny_c, textColor=colors.white)), "", "", ""],
          [Paragraph("<b>Likelihood Score</b>", tiny_c), Paragraph("<b>Descriptor</b>", tiny_c),
           Paragraph("<b>Likelihood of Occurrence</b>", tiny_c), ""],
          ["", "", Paragraph("<b>Number of Occurrence</b>", tiny_c), Paragraph("<b>Probability</b>", tiny_c)]]
    for o in lookups.get("probability", []):
        lm.append([P(o["value"], tiny_c), P(o["label"], tiny_c), P(o.get("description", ""), tiny), P(o.get("range", ""), tiny_c)])
    lmt = Table(lm, colWidths=[CONTENT_W * w for w in (0.095, 0.095, 0.66, 0.15)])
    lmt.setStyle(TableStyle([
        ("SPAN", (0, 0), (3, 0)), ("BACKGROUND", (0, 0), (3, 0), C_BANNER),
        ("SPAN", (2, 1), (3, 1)), ("SPAN", (0, 1), (0, 2)), ("SPAN", (1, 1), (1, 2)),
        ("BACKGROUND", (0, 1), (-1, 1), C_MATRIX_SUB), ("BACKGROUND", (0, 2), (1, 2), C_MATRIX_SUB),
        ("BACKGROUND", (2, 2), (3, 2), C_MATRIX_HEAD),
        ("GRID", (0, 0), (-1, -1), 0.5, C_GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    story += [KeepTogether([lmt]), Spacer(1, 22)]

    # Impact matrix
    im = [[Paragraph("<b>Impact Matrix</b>", ParagraphStyle("imh", parent=tiny_c, textColor=colors.white)), "", ""],
          [Paragraph("<b>Impact Score</b>", tiny_c), Paragraph("<b>Descriptor</b>", tiny_c), Paragraph("<b>Project Impact</b>", tiny_c)]]
    im_style = [("SPAN", (0, 0), (2, 0)), ("BACKGROUND", (0, 0), (2, 0), C_BANNER), ("BACKGROUND", (0, 1), (-1, 1), C_MATRIX_HEAD),
                ("GRID", (0, 0), (-1, -1), 0.5, C_GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    impacts = sorted(lookups.get("impact", []), key=lambda o: -int(o["value"]) if o["value"].isdigit() else 0)
    for i, o in enumerate(impacts, start=2):
        colour = o.get("report_color")
        text_colour = colors.white if colour and colour.upper() in ("#C00000",) else colors.black
        im.append([P(o["value"], tiny_c), Paragraph(escape(o["label"]), ParagraphStyle(f"d{i}", parent=tiny_c, textColor=text_colour)),
                   P(o.get("description", ""), tiny)])
        if colour:
            im_style.append(("BACKGROUND", (1, i), (1, i), colors.HexColor(colour)))
    imt = Table(im, colWidths=[CONTENT_W * w for w in (0.118, 0.103, 0.472)], hAlign="LEFT")
    imt.setStyle(TableStyle(im_style))
    story += [KeepTogether([imt])]

    doc.multiBuild(story)
    return doc.filename.getvalue()
