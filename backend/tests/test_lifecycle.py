from tests.conftest import MANAGER, MODERATOR, codes


def _put_same(client, campaign_id, headers=MANAGER):
    d = client.get(f"/campaigns/{campaign_id}").json()
    body = {k: d[k] for k in ("name", "marketingName", "startDate", "startTime", "endDate", "endTime", "keywords", "audienceType", "weight", "initialCtr")}
    body |= {"topic": {"value": d["topic"]}, "tags": [{"value": t} for t in d["tags"]], "places": [{"value": p} for p in d["places"]]}
    return client.put(f"/campaigns/{campaign_id}", json=body, headers=headers)


def test_role_checked_before_state(client):
    assert codes(client.post("/campaigns/101/approve", headers=MANAGER)) == ["ROLE_FORBIDDEN"]
    assert codes(_put_same(client, 103, headers=MODERATOR)) == ["ROLE_FORBIDDEN"]
    assert codes(client.post("/campaigns/101/approve", headers=MODERATOR)) == ["APPROVE_NOT_ALLOWED"]
    assert codes(client.post("/campaigns/101/activate", headers=MANAGER)) == ["ACTIVATE_NOT_ALLOWED"]
    assert codes(client.post("/campaigns", json={}, headers={})) == ["USER_REQUIRED"]


def test_moderation_cycle(client):
    assert codes(client.post("/campaigns/103/decline", json={}, headers=MODERATOR)) == ["DECLINE_COMMENT_REQUIRED"]
    r = client.post("/campaigns/103/decline", json={"comment": "Добавьте теги"}, headers=MODERATOR)
    assert r.json()["state"] == "NEEDS_WORK"
    assert client.get("/campaigns/103/audit").json()[-1]["comment"] == "Добавьте теги"
    assert client.post("/campaigns/103/to-moderation", headers=MANAGER).json()["state"] == "ON_MODERATION"
    assert client.post("/campaigns/103/approve", headers=MODERATOR).json()["state"] == "APPROVED"
    r = client.post("/campaigns/103/activate", headers=MANAGER).json()
    assert (r["state"], r["published"]) == ("ACTIVE", True)


def test_edit_approved_resets_to_draft(client):
    r = _put_same(client, 107)
    assert r.status_code == 200 and r.json()["state"] == "DRAFT"


def test_edit_active_keeps_showing(client):
    r = _put_same(client, 102).json()
    assert (r["state"], r["published"]) == ("ACTIVE_EDITING", True)
    assert client.post("/campaigns/102/to-moderation", headers=MANAGER).json()["published"] is True


def test_edit_forbidden_states(client):
    assert codes(_put_same(client, 103)) == ["UPDATE_NOT_ALLOWED"]
    assert codes(_put_same(client, 114)) == ["UPDATE_NOT_ALLOWED"]


def test_stop_and_delete(client):
    assert codes(client.delete("/campaigns/102", headers=MANAGER)) == ["DELETE_NOT_ALLOWED"]
    assert codes(client.post("/campaigns/101/stop", headers=MANAGER)) == ["STOP_NOT_ALLOWED"]
    r = client.post("/campaigns/102/stop", headers=MANAGER).json()
    assert (r["state"], r["published"]) == ("STOPPED", False)

    assert client.delete("/campaigns/101", headers=MANAGER).status_code == 204
    assert client.get("/campaigns/101").status_code == 404
    assert client.get("/campaigns/101/audit").status_code == 404


def test_update_diff_in_audit(client):
    d = client.get("/campaigns/101").json()
    banner = d["banners"][0]
    banner["content"]["title"] = "Новый заголовок"
    client.put("/campaigns/101/banners/201", json={k: banner[k] for k in ("name", "bannerTypeId", "content")}, headers=MANAGER)
    last = client.get("/campaigns/101/audit").json()[-1]
    assert last["entity"] == "BANNER" and last["action"] == "UPDATE"
    assert last["changes"] == {"content.title": {"from": "Премиальная карта — осенняя акция", "to": "Новый заголовок"}}
