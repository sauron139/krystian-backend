"""Management commands: `python -m app.cli <command>`.

seed                 Insert placeholder content where missing (idempotent)
create-admin EMAIL   Create the admin user, or reset its password
                     (password from ADMIN_PASSWORD env var, else prompted)
ensure-dev-admin     Create the admin from DEV_ADMIN_EMAIL/DEV_ADMIN_PASSWORD (dev only)
export-openapi PATH  Write the OpenAPI spec as JSON (used to generate client types)
"""

import argparse
import asyncio
import getpass
import json
import os
import sys
from pathlib import Path

from app.core.cache import invalidate_public_cache
from app.core.config import get_settings
from app.db.session import SessionLocal, engine


async def _seed() -> None:
    from app.seed import seed

    async with SessionLocal() as session:
        done = await seed(session)
    await invalidate_public_cache()
    print(f"Seeded: {', '.join(done)}" if done else "Nothing to seed; content already exists.")


async def _create_admin(email: str, password: str) -> None:
    from app.services.auth import upsert_admin

    async with SessionLocal() as session:
        user = await upsert_admin(session, email, password)
    print(f"Admin ready: {user.email}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed")
    p_admin = sub.add_parser("create-admin")
    p_admin.add_argument("email")
    sub.add_parser("ensure-dev-admin")
    p_spec = sub.add_parser("export-openapi")
    p_spec.add_argument("path", type=Path)
    args = parser.parse_args()

    async def run() -> None:
        try:
            if args.command == "seed":
                await _seed()
            elif args.command == "create-admin":
                password = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Password: ")
                if len(password) < 12:
                    sys.exit("Password must be at least 12 characters.")
                await _create_admin(args.email, password)
            elif args.command == "ensure-dev-admin":
                s = get_settings()
                if s.is_production or not (s.dev_admin_email and s.dev_admin_password):
                    print("Skipping dev admin (production, or DEV_ADMIN_* not set).")
                    return
                await _create_admin(str(s.dev_admin_email), s.dev_admin_password.get_secret_value())
            elif args.command == "export-openapi":
                from app.main import app

                args.path.write_text(json.dumps(app.openapi(), indent=2) + "\n")
                print(f"Wrote {args.path}")
        finally:
            await engine.dispose()

    asyncio.run(run())


if __name__ == "__main__":
    main()
