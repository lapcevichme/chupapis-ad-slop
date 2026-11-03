import asyncio
from dataclasses import dataclass
from typing import Any, Self

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import Settings

_MISSING_CODES = {"404", "NoSuchKey", "NotFound"}


@dataclass(frozen=True, slots=True)
class StoredObject:
    data: bytes
    content_type: str


class ObjectStorage:
    """S3-совместимое хранилище. boto3 блокирующий, поэтому каждый вызов уходит в поток,
    а снаружи видны только async-методы. Бакет закрытый: файлы раздаёт API (/media)."""

    def __init__(
        self,
        *,
        endpoint: str,
        region: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        use_path_style: bool,
    ) -> None:
        config = Config(
            signature_version="s3v4",
            s3={"addressing_style": "path" if use_path_style else "auto"},
        )
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=config,
        )
        self._region = region
        self.bucket = bucket

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        return cls(
            endpoint=settings.storage_endpoint,
            region=settings.storage_region,
            access_key=settings.storage_access_key,
            secret_key=settings.storage_secret_key.get_secret_value(),
            bucket=settings.storage_bucket,
            use_path_style=settings.storage_use_path_style,
        )

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )

    async def get(self, key: str) -> StoredObject | None:
        try:
            response = await asyncio.to_thread(self._client.get_object, Bucket=self.bucket, Key=key)
            data = await asyncio.to_thread(response["Body"].read)
        except ClientError as exc:
            if str(exc.response.get("Error", {}).get("Code")) in _MISSING_CODES:
                return None
            raise
        return StoredObject(data, response.get("ContentType") or "application/octet-stream")

    async def delete(self, key: str) -> None:
        # Удаление в S3 идемпотентно: отсутствующий ключ не ошибка.
        await asyncio.to_thread(self._client.delete_object, Bucket=self.bucket, Key=key)

    async def ping(self) -> None:
        await asyncio.to_thread(self._client.head_bucket, Bucket=self.bucket)

    async def ensure_bucket(self) -> None:
        """Для dev и тестов: создаёт бакет, если его ещё нет. В проде бакет заводит инфраструктура."""
        try:
            await self.ping()
        except ClientError:
            kwargs: dict[str, Any] = {"Bucket": self.bucket}
            if self._region != "us-east-1":
                kwargs["CreateBucketConfiguration"] = {"LocationConstraint": self._region}
            await asyncio.to_thread(self._client.create_bucket, **kwargs)
