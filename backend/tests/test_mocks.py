"""Моки организаторов валидны и дают те же warnings, что `campaign_warnings.json`."""

import json

from app.core.config import BACKEND_DIR
from app.infra.creative_validation import validate_banner_json, validate_content_json

LIMITS = {1: ("STORY", 100, 500), 2: ("SMART_BANNER", 250, 1000)}


def _seed(name):
    return json.loads(((BACKEND_DIR / "seed") / f"{name}.json").read_text(encoding="utf-8"))


def test_mock_banners_pass_schema():
    for banner in _seed("campaign_banners"):
        code, title_max, text_max = LIMITS[banner["bannerTypeId"]]
        _, errors = validate_banner_json(
            banner["content"], type_code=code, title_max=title_max, text_max=text_max
        )
        assert errors == [], (banner["id"], errors)


def test_mock_contents_pass_schema():
    for content in _seed("campaign_contents"):
        _, errors = validate_content_json(content["content"])
        assert errors == [], (content["id"], errors)


def test_warnings_match_mocks(client):
    expected = {row["campaignId"]: row["warnings"] for row in _seed("campaign_warnings")}
    for campaign in client.get("/campaigns").json():
        report = client.get(f"/campaigns/{campaign['id']}/warnings").json()
        assert report["errors"] == [], (campaign["id"], report["errors"])
        assert report["warnings"] == expected.get(campaign["id"], []), campaign["id"]


def test_details_shape(client):
    details = client.get("/campaigns/101").json()
    assert details["topic"] == "SALES"
    assert details["tags"] == [4, 3]
    assert details["places"] == [2]
    assert details["segments"] == {
        "included": ["CHANNEL_VIP", "CITY_MSK"],
        "excluded": ["EXC_UNSUBSCRIBED"],
    }
    assert [b["id"] for b in details["banners"]] == [201]
    assert [c["id"] for c in details["creatives"]] == [401, 402]


def test_decline_comment_in_audit(client):
    audit = client.get("/campaigns/104/audit").json()
    assert audit[-1]["action"] == "DECLINE"
    assert "теги" in audit[-1]["comment"]
