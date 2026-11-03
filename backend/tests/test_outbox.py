"""Побочные эффекты идут через outbox: после коммита, с повторами и без дублей при откате."""

from datetime import timedelta

from sqlalchemy import select

from app.db.models import OutboxEvent
from app.domain.events import OutboxStatus, Topic
from app.service.outbox import OutboxDispatcher, build_handlers, retry_delay
from tests.conftest import MANAGER, MODERATOR


class RecordingNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.fail_with: Exception | None = None

    async def send(self, text: str) -> None:
        if self.fail_with is not None:
            raise self.fail_with
        self.messages.append(text)


def events(client) -> list[OutboxEvent]:
    async def load(app):
        async with app.state.db.unit_of_work() as uow:
            rows = await uow.session.scalars(select(OutboxEvent).order_by(OutboxEvent.created_at))
            return list(rows)

    return client.portal.call(load, client.app)


def run_once(client, notifier, *, max_attempts=3) -> int:
    dispatcher = OutboxDispatcher(
        client.app.state.db, build_handlers(notifier), batch_size=50, max_attempts=max_attempts
    )
    return client.portal.call(dispatcher.run_once)


def test_decisions_are_delivered_after_commit_not_during_the_request(client):
    notifier = RecordingNotifier()
    client.post(
        "/campaigns/103/decline", json={"comment": "Нужен другой заголовок"}, headers=MODERATOR
    )
    client.post("/campaigns/103/to-moderation", headers=MANAGER)

    assert notifier.messages == []
    assert [e.topic for e in events(client)] == [
        Topic.CAMPAIGN_REVIEWED,
        Topic.CAMPAIGN_SENT_TO_MODERATION,
    ]
    assert run_once(client, notifier) == 2
    assert "возвращена на доработку" in notifier.messages[0]
    assert "Нужен другой заголовок" in notifier.messages[0]
    assert "ждёт модерации" in notifier.messages[1]
    assert all(e.status is OutboxStatus.DONE for e in events(client))
    assert run_once(client, notifier) == 0


def test_failed_request_leaves_no_event(client):
    # Без комментария возврат отклоняется, а вместе с ним откатывается и событие.
    response = client.post("/campaigns/103/decline", json={}, headers=MODERATOR)
    assert response.status_code == 400
    assert events(client) == []


def test_handler_failure_is_retried_with_backoff_then_goes_dead(client):
    client.post("/campaigns/103/decline", json={"comment": "Добавьте теги"}, headers=MODERATOR)
    notifier = RecordingNotifier()
    notifier.fail_with = RuntimeError("telegram is down")

    assert run_once(client, notifier, max_attempts=2) == 1
    (event,) = events(client)
    assert event.status is OutboxStatus.PENDING and event.attempts == 1
    assert "telegram is down" in (event.last_error or "")

    # Повтор отложен: сразу после сбоя событие не берётся.
    assert run_once(client, notifier, max_attempts=2) == 0

    async def make_due(app):
        async with app.state.db.unit_of_work() as uow:
            row = await uow.session.scalar(select(OutboxEvent))
            row.available_at = row.available_at - timedelta(hours=1)

    client.portal.call(make_due, client.app)
    assert run_once(client, notifier, max_attempts=2) == 1
    assert events(client)[0].status is OutboxStatus.DEAD


def test_activation_exports_to_cbro_and_notifies(client):
    client.post("/campaigns/103/decline", json={"comment": "Добавьте теги"}, headers=MODERATOR)
    client.post("/campaigns/103/to-moderation", headers=MANAGER)
    client.post("/campaigns/103/approve", headers=MODERATOR)
    assert client.post("/campaigns/103/activate", headers=MANAGER).json()["published"] is True

    notifier = RecordingNotifier()
    assert run_once(client, notifier) == 4
    assert "запущена" in notifier.messages[-1]


def test_backoff_grows_and_is_capped():
    assert retry_delay(1) < retry_delay(3) < retry_delay(5)
    assert retry_delay(50) == timedelta(hours=1)
