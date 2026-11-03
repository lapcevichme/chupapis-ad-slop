import asyncio
import secrets
from functools import cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# argon2id with the RFC 9106 "low memory" profile (the library defaults): ~50 ms per hash.
_hasher = PasswordHasher()


@cache
def _dummy_hash() -> str:
    return _hasher.hash(secrets.token_hex(16))


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hasher.hash, password)


async def verify_password(password: str, password_hash: str | None) -> bool:
    """
    Verify off the event loop. With no hash (unknown email) we still burn one verification
    against a dummy hash, so response time does not reveal which emails are registered.
    """
    target = password_hash if password_hash is not None else await asyncio.to_thread(_dummy_hash)
    try:
        await asyncio.to_thread(_hasher.verify, target, password)
    except (VerificationError, InvalidHashError):
        return False
    return password_hash is not None


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)
