from collections.abc import Callable
from typing import Any

import httpx


class ApiCallError(Exception):
    def __init__(self, status: int, errors: list[dict[str, Any]]):
        self.status = status
        self.errors = errors
        super().__init__("; ".join(f"{e.get('code')}: {e.get('message')}" for e in errors))


class CampaignsApi:
    def __init__(
        self,
        user: str,
        role: str,
        *,
        base_url: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-User": user, "X-Role": role},
            transport=transport,
            timeout=30,
        )

    async def __aenter__(self) -> "CampaignsApi":
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self._client.aclose()

    async def request(self, method: str, path: str, body: Any = None) -> Any:
        response = await self._client.request(method, path, json=body)
        if response.status_code >= 400:
            try:
                errors = response.json().get("errors") or []
            except ValueError:
                errors = []
            raise ApiCallError(
                response.status_code,
                errors
                or [{"code": f"HTTP_{response.status_code}", "message": response.text[:300]}],
            )
        return response.json() if response.content else None

    async def get(self, path: str) -> Any:
        return await self.request("GET", path)


ApiFactory = Callable[[str, str], CampaignsApi]
