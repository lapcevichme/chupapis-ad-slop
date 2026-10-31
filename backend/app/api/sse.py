import json
from collections.abc import AsyncIterator

from app.domain.chat import StreamEvent


async def encode_events(events: AsyncIterator[StreamEvent]) -> AsyncIterator[str]:
    async for event in events:
        if event.event:
            yield f"event: {event.event}\ndata: {json.dumps(event.data, ensure_ascii=False)}\n\n"
        else:
            yield ": keep-alive\n\n"
