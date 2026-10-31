"""Заглушка Content Broker (§5, mocks/cbro_export.json): всегда успех."""

from fastapi import APIRouter

from app.domain.audit import utcnow
from app.schemas import api

router = APIRouter(prefix="/mock/cbro", tags=["cbro"])


def export_campaign(campaign_id: int) -> api.CbroExportResponse:
    return api.CbroExportResponse(status="OK", exportedAt=utcnow())


@router.post("/export", response_model=api.CbroExportResponse)
def cbro_export(body: api.CbroExportRequest):
    return export_campaign(body.campaignId)
