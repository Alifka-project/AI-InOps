"""Report generation endpoint — returns a downloadable PDF."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from .. import report
from ..models import ReportRequest

router = APIRouter(prefix="/api", tags=["report"])


@router.post("/report")
def generate_report(req: ReportRequest) -> StreamingResponse:
    pdf = report.build_report(
        req.dataset.as_dict(),
        req.scenario.value,
        req.alpha,
        req.beta,
        req.horizon,
        req.service_level,
        auto_tune=req.auto_tune,
    )
    name = "digital-twin-report"
    suffix = "sample" if req.dataset.meta.is_sample else req.scenario.value
    import io

    return StreamingResponse(
        io.BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{name}-{suffix}.pdf"'},
    )
