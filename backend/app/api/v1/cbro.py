"""Заглушка Content Broker (§5, mocks/cbro_export.json): всегда успех."""

from fastapi import APIRouter

from app.contracts import campaigns as api
from app.infra.cbro import export_campaign

router = APIRouter(prefix="/mock/cbro", tags=["cbro"])


@router.post("/export", response_model=api.CbroExportResponse)
def cbro_export(body: api.CbroExportRequest) -> api.CbroExportResponse:
    return api.CbroExportResponse.from_domain(export_campaign(body.campaignId))
