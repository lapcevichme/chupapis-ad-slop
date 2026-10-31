"""Сквозной сценарий §9 task.md: бриф по вкладу → кампания с креативами → ON_MODERATION."""

from tests.conftest import MANAGER, codes

CAMPAIGN = {
    "name": "Вклад 16%: Москва и СПб",
    "marketingName": "Вклад под 16% до конца года",
    "startDate": "2026-11-05",
    "startTime": "00:00",
    "endDate": "2026-12-31",
    "endTime": "23:59",
    "topic": {"value": "SALES", "label": "Продажи"},
    "tags": [{"value": 5, "label": "Вклад"}],
    "audienceType": "SEGMENTED",
    "places": [{"value": 1, "label": "mainScreenStories"}],
}

STORY = {
    "name": "Сторис: вклад 16%",
    "bannerTypeId": 1,
    "content": {
        "title": "Вклад под 16% годовых",
        "text": "Откройте онлайн за 2 минуты",
        "titleStyle": {"fontSize": 28, "fontWeight": "bold", "textColor": "#FFFFFFFF"},
        "background": {"color": "#21A038FF"},
        "buttonName": "Подробнее",
        "actionType": "default",
    },
}

PROMO = {
    "name": "Промо-экран: вклад 16%",
    "contentType": "PROMO",
    "content": {
        "role": "promo",
        "component": {
            "role": "linearContainer",
            "axis": "v",
            "components": [
                {"role": "text", "format": "html", "text": "<b>16% годовых</b> до 31 декабря"},
                {
                    "role": "button",
                    "text": "Открыть вклад",
                    "actionType": "openSmartLink",
                    "link": {"iOS": "mobilebank://deposits/open", "android": "mobilebank://deposits/open"},
                },
            ],
        },
    },
}


def test_brief_to_moderation(client):
    created = client.post("/campaigns", json=CAMPAIGN, headers=MANAGER)
    assert created.status_code == 201, created.json()
    cid = created.json()["id"]
    assert created.json()["state"] == "DRAFT"

    # SEGMENTED без сегментов на модерацию не уходит.
    blocked = client.post(f"/campaigns/{cid}/to-moderation", headers=MANAGER)
    assert codes(blocked) == ["SEGMENTS_REQUIRED"]

    segments = {"included": ["AGE_26_45", "CITY_MSK", "CITY_SPB"], "excluded": ["EXC_UNSUBSCRIBED"]}
    assert client.put(f"/campaigns/{cid}/segments", json=segments, headers=MANAGER).json() == segments

    banner = client.post(f"/campaigns/{cid}/banners", json=STORY, headers=MANAGER)
    assert banner.status_code == 201, banner.json()
    content = client.post(f"/campaigns/{cid}/contents", json=PROMO, headers=MANAGER)
    assert content.status_code == 201, content.json()
    for channel in ("iOS", "ANDROID"):
        creative = {"name": f"Креатив {channel}", "bannerId": banner.json()["id"], "contentId": content.json()["id"], "channelCode": channel}
        assert client.post(f"/campaigns/{cid}/creatives", json=creative, headers=MANAGER).status_code == 201

    assert client.get(f"/campaigns/{cid}/warnings").json() == {"errors": [], "warnings": []}

    sent = client.post(f"/campaigns/{cid}/to-moderation", headers=MANAGER)
    assert sent.status_code == 200, sent.json()
    assert sent.json()["state"] == "ON_MODERATION"

    actions = [(e["entity"], e["action"]) for e in client.get(f"/campaigns/{cid}/audit").json()]
    assert actions == [
        ("CAMPAIGN", "CREATE"),
        ("SEGMENTS", "UPDATE"),
        ("BANNER", "CREATE"),
        ("CONTENT", "CREATE"),
        ("CREATIVE", "CREATE"),
        ("CREATIVE", "CREATE"),
        ("CAMPAIGN", "TO_MODERATION"),
    ]


def test_new_tag_and_place(client):
    tag = client.post("/tags", json={"name": "Ипотека"}, headers=MANAGER)
    assert tag.status_code == 201
    assert codes(client.post("/tags", json={"name": "Ипотека"}, headers=MANAGER)) == ["TAG_NAME_DUPLICATE"]

    place = client.post("/places", json={"code": "mortgageScreen", "description": "Экран ипотеки"}, headers=MANAGER)
    assert place.json()["state"] == "ACTIVE" and place.json()["defaultBanner"] is None

    body = CAMPAIGN | {"tags": [{"value": tag.json()["id"]}], "places": [{"value": place.json()["id"]}]}
    cid = client.post("/campaigns", json=body, headers=MANAGER).json()["id"]
    # Место без defaultBanner считается покрытым (§7.2 mock-data).
    assert client.get(f"/campaigns/{cid}/warnings").json()["warnings"] == []
