from tests.conftest import MANAGER, codes
from tests.test_scenario import CAMPAIGN


def _banner_201(client):
    return next(b for b in client.get("/campaigns/101").json()["banners"] if b["id"] == 201)


def test_title_limit_on_draft(client):
    banner = _banner_201(client)
    banner["bannerTypeId"] = 1  # STORY: лимит 100, а креативы 101 в iOS/ANDROID допустимы для STORY
    banner["content"]["title"] = "А" * 132
    r = client.put("/campaigns/101/banners/201", json={k: banner[k] for k in ("name", "bannerTypeId", "content")}, headers=MANAGER)
    assert r.status_code == 400
    error = r.json()["errors"][0]
    assert error["code"] == "BANNER_TITLE_TOO_LONG"
    assert error["field"] == "content.title"
    assert "132" in error["message"] and "100" in error["message"]


def test_invalid_banner_json(client):
    body = {
        "name": "Битый",
        "bannerTypeId": 2,
        "content": {
            "actionType": "doneCampaign",
            "link": {"web": "https://example.com"},
            "titleStyle": {"fontSize": 99, "textColor": "red"},
            "extra": 1,
        },
    }
    r = client.post("/campaigns/108/banners", json=body, headers=MANAGER)
    assert r.status_code == 400
    assert set(codes(r)) == {"FONT_SIZE_INVALID", "COLOR_INVALID", "UNKNOWN_FIELD"}

    body["content"] = {"actionType": "doneCampaign", "link": {"web": "https://example.com"}}
    assert codes(client.post("/campaigns/108/banners", json=body, headers=MANAGER)) == ["LINK_FORBIDDEN"]
    body["content"] = {"actionType": "externalLink"}
    assert codes(client.post("/campaigns/108/banners", json=body, headers=MANAGER)) == ["LINK_REQUIRED"]
    body["content"] = {"actionType": "default", "image": {"url": "http://example.com/a.png"}}
    assert codes(client.post("/campaigns/108/banners", json=body, headers=MANAGER)) == ["IMAGE_URL_INVALID"]


def test_invalid_content_json(client):
    body = {
        "name": "Битый контент",
        "contentType": "PROMO",
        "content": {"role": "promo", "component": {"role": "linearContainer", "axis": "h", "components": [{"role": "text", "text": "x"}, {"role": "video"}]}},
    }
    r = client.post("/campaigns/108/contents", json=body, headers=MANAGER)
    assert set(codes(r)) == {"CONTENT_AXIS_INVALID", "TEXT_FORMAT_REQUIRED", "CONTENT_ROLE_INVALID"}


def test_story_in_web_is_rejected(client):
    banner = client.post(
        "/campaigns/108/banners", json={"name": "Сторис", "bannerTypeId": 1, "content": {"actionType": "default"}}, headers=MANAGER
    ).json()
    r = client.post("/campaigns/108/creatives", json={"name": "Web", "bannerId": banner["id"], "channelCode": "WEB"}, headers=MANAGER)
    assert codes(r) == ["CHANNEL_NOT_ALLOWED"]
    r = client.post("/campaigns/108/creatives", json={"name": "web", "bannerId": banner["id"], "channelCode": "web"}, headers=MANAGER)
    assert r.status_code == 404 and codes(r) == ["ENTITY_NOT_FOUND"]


def test_campaign_header_errors(client):
    r = client.post("/campaigns", json=CAMPAIGN | {"endDate": "2026-11-01"}, headers=MANAGER)
    assert codes(r) == ["DATE_RANGE_INVALID"]
    r = client.post("/campaigns", json=CAMPAIGN | {"startTime": "25:00", "topic": {"value": "NOPE"}, "places": []}, headers=MANAGER)
    assert r.status_code == 400
    assert set(codes(r)) == {"TIME_FORMAT_INVALID", "TOPIC_INVALID", "PLACES_REQUIRED"}
    r = client.post("/campaigns", json=CAMPAIGN | {"name": "Сомелье: подбор вина"}, headers=MANAGER)
    assert codes(r) == ["NAME_DUPLICATE"]
    r = client.post("/campaigns", json=CAMPAIGN | {"tags": [{"value": 999}]}, headers=MANAGER)
    assert r.status_code == 404 and r.json()["errors"][0]["field"] == "tags[0].value"


def test_segments_rules(client):
    r = client.put("/campaigns/108/segments", json={"included": ["CITY_MSK"]}, headers=MANAGER)
    assert codes(r) == ["SEGMENTS_FORBIDDEN_FOR_ALL_USERS"]
    r = client.put("/campaigns/101/segments", json={"included": ["SEG_DRAFT_WINTER", "NOPE"]}, headers=MANAGER)
    assert codes(r) == ["SEGMENT_NOT_ACTIVE", "SEGMENT_NOT_FOUND"]
    # Смена на ALL_USERS при сохранённых сегментах запрещена.
    details = client.get("/campaigns/101").json()
    body = {k: details[k] for k in ("name", "startDate", "startTime", "endDate", "endTime")}
    body |= {"topic": {"value": "SALES"}, "audienceType": "ALL_USERS", "places": [{"value": 2}]}
    assert codes(client.put("/campaigns/101", json=body, headers=MANAGER)) == ["SEGMENTS_FORBIDDEN_FOR_ALL_USERS"]
