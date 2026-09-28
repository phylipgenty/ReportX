"""
Report generation (README §38): select project -> select period -> load
project state -> review (JSON) -> export Word / PDF. The PDF follows the
FMDQ April 2025 Project Status Report format (services/report_pdf.py).
"""
import re
from typing import Optional

from fastapi import APIRouter, Depends, Request, Response

from app.models.report import ReportRequest, ProjectStatusReport
from app.services import auth, domain
from app.services.report import build_report
from app.services.report_pdf import render_pdf
from app.services.report_render import render_docx

router = APIRouter(tags=["reports"])

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@router.post("/projects/{project_id}/report", response_model=ProjectStatusReport)
def review_report(project_id: str, req: ReportRequest, request: Request) -> ProjectStatusReport:
    return build_report(project_id, req, domain.actor(request))


def _request(start_date, end_date, state_id, use_current, report_author, executive_sponsor) -> ReportRequest:
    return ReportRequest(start_date=start_date, end_date=end_date, state_id=state_id or None,
                         use_current=use_current, report_author=report_author,
                         executive_sponsor=executive_sponsor)


def _filename(report: ProjectStatusReport, ext: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", "_", report.metadata.project_title).strip("_")
    return f"{report.metadata.project_id}_{safe}_Status_Report_{report.metadata.reporting_period.end_date}.{ext}"


def _file(content: bytes, media_type: str, filename: str, inline: bool = False) -> Response:
    disposition = "inline" if inline else "attachment"
    return Response(content, media_type=media_type,
                    headers={"Content-Disposition": f'{disposition}; filename="{filename}"'})


@router.get("/projects/{project_id}/report/word", dependencies=[Depends(auth.require("report.export"))])
def export_word(project_id: str, start_date: str, end_date: str, request: Request, state_id: Optional[str] = None,
                use_current: bool = False, report_author: Optional[str] = None,
                executive_sponsor: Optional[str] = None):
    report = build_report(project_id, _request(start_date, end_date, state_id, use_current,
                                               report_author, executive_sponsor), domain.actor(request))
    return _file(render_docx(report), DOCX_MIME, _filename(report, "docx"))


@router.get("/projects/{project_id}/report/pdf", dependencies=[Depends(auth.require("report.export"))])
def export_pdf(project_id: str, start_date: str, end_date: str, request: Request, state_id: Optional[str] = None,
               use_current: bool = False, report_author: Optional[str] = None,
               executive_sponsor: Optional[str] = None, inline: bool = False):
    """inline=true opens the PDF in the browser instead of downloading it."""
    report = build_report(project_id, _request(start_date, end_date, state_id, use_current,
                                               report_author, executive_sponsor), domain.actor(request))
    return _file(render_pdf(report), "application/pdf", _filename(report, "pdf"), inline=inline)
