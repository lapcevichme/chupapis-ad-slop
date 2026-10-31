from app.domain.audit import utcnow
from app.domain.views import CbroExportResponse


def export_campaign(campaign_id: int) -> CbroExportResponse:
    return CbroExportResponse(status="OK", exportedAt=utcnow())
