import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Tag
from tests.conftest import MANAGER
from tests.test_scenario import CAMPAIGN


def test_unit_of_work_rolls_back_flushed_changes(client):
    async def exercise():
        try:
            async with client.app.state.db.unit_of_work() as uow:
                uow.session.add(Tag(name="Не должен сохраниться"))
                await uow.flush()
                raise RuntimeError("rollback")
        except RuntimeError:
            pass

    client.portal.call(exercise)
    assert all(tag["name"] != "Не должен сохраниться" for tag in client.get("/tags").json())


def test_commit_failure_returns_error_and_rolls_back_campaign_and_audit(client, monkeypatch):
    original_commit = AsyncSession.commit

    async def failed_commit(_session):
        raise RuntimeError("commit failed")

    async def request():
        transport = httpx.ASGITransport(app=client.app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
            return await http.post("/campaigns", headers=MANAGER, json=CAMPAIGN)

    monkeypatch.setattr(AsyncSession, "commit", failed_commit)
    response = client.portal.call(request)
    monkeypatch.setattr(AsyncSession, "commit", original_commit)
    assert response.status_code == 500
    assert all(row["name"] != CAMPAIGN["name"] for row in client.get("/campaigns").json())
