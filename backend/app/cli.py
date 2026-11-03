import argparse
import asyncio
import getpass
import os

from app.core.config import get_settings
from app.core.security.passwords import hash_password
from app.db.database import Database
from app.db.models import User
from app.domain.enums import Role
from app.domain.users import normalize_email
from app.infra.checkpointer import setup_checkpointer


async def create_user(email: str, username: str, password: str, role: Role) -> str:
    """Создаёт пользователя или меняет роль у существующего. Возвращает, что произошло."""
    db = Database(get_settings())
    try:
        async with db.unit_of_work() as uow:
            email = normalize_email(email)
            user = await uow.users.get_by_email(email)
            if user is not None:
                user.role = role
                user.auth_version += 1
                return f"{email}: роль {role.value}"
            uow.users.add(
                User(
                    email=email,
                    username=username,
                    password_hash=await hash_password(password),
                    role=role,
                )
            )
            return f"создан {email} ({username}), роль {role.value}"
    finally:
        await db.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    user = commands.add_parser("create-user", help="создать пользователя или сменить роль")
    user.add_argument("email")
    user.add_argument("--username", help="по умолчанию часть почты до @")
    user.add_argument("--role", choices=[r.value for r in Role], default=Role.ADMIN.value)
    commands.add_parser("setup-checkpointer", help="создать таблицы чекпоинтов агента")
    args = parser.parse_args()

    if args.command == "setup-checkpointer":
        asyncio.run(setup_checkpointer(get_settings()))
        print("Таблицы чекпоинтов готовы")
        return
    password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Пароль: ")
    username = args.username or args.email.split("@")[0]
    print(asyncio.run(create_user(args.email, username, password, Role(args.role))))


if __name__ == "__main__":
    main()
