"""Persistent trial quotas, rate limits, and account-scoped resume history."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

from sqlalchemy import BigInteger, Column, Index, Integer, MetaData, String, Table, Text, delete, select, text
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert


class TrialLimitExceeded(RuntimeError):
    """A trial quota or rate limit prevented a request from starting."""


class UsageStore:
    def __init__(self, database_url: str | None, *, require_external_database: bool = False):
        if database_url:
            database_url = database_url.strip()
            if database_url.startswith("postgres://"):
                database_url = "postgresql+psycopg://" + database_url.removeprefix("postgres://")
            elif database_url.startswith("postgresql://"):
                database_url = "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
        elif require_external_database:
            raise RuntimeError(
                "Set DATABASE_URL to a persistent PostgreSQL database before starting the Render service."
            )
        else:
            instance_dir = Path(__file__).resolve().parent / "instance"
            instance_dir.mkdir(parents=True, exist_ok=True)
            database_url = f"sqlite:///{(instance_dir / 'resumate.sqlite3').as_posix()}"

        if require_external_database and not database_url.startswith(("postgresql+psycopg://", "postgresql://", "postgres://")):
            raise RuntimeError("DATABASE_URL must point to a persistent PostgreSQL database on Render.")

        engine_options = {"pool_pre_ping": True}
        if database_url.startswith("sqlite:"):
            engine_options["connect_args"] = {"check_same_thread": False, "timeout": 15}
        self.engine = create_engine(database_url, **engine_options)

        metadata = MetaData()
        self.account_usage = Table(
            "resumate_trial_usage",
            metadata,
            Column("account_key", String(64), primary_key=True),
            Column("feature", String(32), primary_key=True),
            Column("count", Integer, nullable=False),
            Column("updated_at", BigInteger, nullable=False),
        )
        self.rate_windows = Table(
            "resumate_rate_windows",
            metadata,
            Column("scope", String(16), primary_key=True),
            Column("bucket_key", String(64), primary_key=True),
            Column("window_start", BigInteger, primary_key=True),
            Column("count", Integer, nullable=False),
            Column("updated_at", BigInteger, nullable=False),
        )
        Index("ix_resumate_rate_window_start", self.rate_windows.c.window_start)
        self.resume_history = Table(
            "resumate_resume_history",
            metadata,
            Column("history_id", String(32), primary_key=True),
            Column("account_key", String(64), nullable=False),
            Column("payload", Text, nullable=False),
            Column("created_at", BigInteger, nullable=False),
        )
        Index(
            "ix_resumate_resume_history_account_created",
            self.resume_history.c.account_key,
            self.resume_history.c.created_at,
        )
        metadata.create_all(self.engine)

    @staticmethod
    def account_key(auth0_subject: str) -> str:
        """Return a stable pseudonymous key without storing the Auth0 subject itself."""
        return hashlib.sha256(auth0_subject.encode("utf-8")).hexdigest()

    @staticmethod
    def _insert_for_connection(connection, table):
        dialect = connection.dialect.name
        if dialect == "postgresql":
            return postgresql_insert(table)
        if dialect == "sqlite":
            return sqlite_insert(table)
        raise RuntimeError(f"Unsupported database dialect: {dialect}")

    def _increment_with_limit(
        self,
        connection,
        table,
        values: dict,
        conflict_columns: list,
        limit: int,
        updated_at: int,
    ) -> int | None:
        statement = self._insert_for_connection(connection, table).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=conflict_columns,
            set_={"count": table.c.count + 1, "updated_at": updated_at},
            where=table.c.count < limit,
        ).returning(table.c.count)
        return connection.execute(statement).scalar_one_or_none()

    def reserve_rate_limits(
        self,
        *,
        account_key: str,
        ip_key: str,
        account_limit: int,
        ip_limit: int,
        now: int,
    ) -> None:
        current_hour = (now // 3600) * 3600
        with self.engine.begin() as connection:
            # Keep only the current and immediately preceding hour of pseudonymous IP data.
            connection.execute(
                delete(self.rate_windows).where(self.rate_windows.c.window_start < current_hour - 3600)
            )
            for scope, bucket_key, limit in (
                ("account", account_key, account_limit),
                ("ip", ip_key, ip_limit),
            ):
                count = self._increment_with_limit(
                    connection,
                    self.rate_windows,
                    {
                        "scope": scope,
                        "bucket_key": bucket_key,
                        "window_start": current_hour,
                        "count": 1,
                        "updated_at": now,
                    },
                    [self.rate_windows.c.scope, self.rate_windows.c.bucket_key, self.rate_windows.c.window_start],
                    limit,
                    now,
                )
                if count is None:
                    raise TrialLimitExceeded(
                        "This account or network has reached its hourly trial request limit. Please try again later."
                    )

    def reserve_feature(self, *, account_key: str, feature: str, limit: int, now: int) -> int:
        with self.engine.begin() as connection:
            count = self._increment_with_limit(
                connection,
                self.account_usage,
                {"account_key": account_key, "feature": feature, "count": 1, "updated_at": now},
                [self.account_usage.c.account_key, self.account_usage.c.feature],
                limit,
                now,
            )
            if count is None:
                raise TrialLimitExceeded(
                    f"This account has used all {limit} trial requests for this feature."
                )
            return count

    def remaining(self, *, account_key: str, limits: dict[str, int]) -> dict[str, int]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(self.account_usage.c.feature, self.account_usage.c.count).where(
                    self.account_usage.c.account_key == account_key
                )
            )
            used = {feature: count for feature, count in rows}
        return {feature: max(0, limit - used.get(feature, 0)) for feature, limit in limits.items()}

    def delete_account(self, *, account_key: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                delete(self.account_usage).where(self.account_usage.c.account_key == account_key)
            )
            connection.execute(
                delete(self.rate_windows).where(
                    (self.rate_windows.c.scope == "account")
                    & (self.rate_windows.c.bucket_key == account_key)
                )
            )
            connection.execute(
                delete(self.resume_history).where(self.resume_history.c.account_key == account_key)
            )

    def save_resume_history(
        self,
        *,
        account_key: str,
        payload: dict,
        created_at: int,
        max_entries: int = 25,
    ) -> dict:
        history_id = uuid4().hex
        stored_payload = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        with self.engine.begin() as connection:
            connection.execute(
                self.resume_history.insert().values(
                    history_id=history_id,
                    account_key=account_key,
                    payload=stored_payload,
                    created_at=created_at,
                )
            )
            retained_ids = select(self.resume_history.c.history_id).where(
                self.resume_history.c.account_key == account_key
            ).order_by(self.resume_history.c.created_at.desc(), self.resume_history.c.history_id.desc()).limit(max_entries)
            connection.execute(
                delete(self.resume_history).where(
                    (self.resume_history.c.account_key == account_key)
                    & self.resume_history.c.history_id.not_in(retained_ids)
                )
            )
        return {**payload, "id": history_id, "created_at": created_at}

    def list_resume_history(self, *, account_key: str, max_entries: int = 25) -> list[dict]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(
                    self.resume_history.c.history_id,
                    self.resume_history.c.payload,
                    self.resume_history.c.created_at,
                )
                .where(self.resume_history.c.account_key == account_key)
                .order_by(self.resume_history.c.created_at.desc(), self.resume_history.c.history_id.desc())
                .limit(max_entries)
            )
            return [
                {**json.loads(payload), "id": history_id, "created_at": created_at}
                for history_id, payload, created_at in rows
            ]

    def clear_resume_history(self, *, account_key: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                delete(self.resume_history).where(self.resume_history.c.account_key == account_key)
            )

    def ping(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

