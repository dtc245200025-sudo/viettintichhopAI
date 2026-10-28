from contextlib import contextmanager
from typing import Any, Iterator

from mysql.connector import pooling


def _sql(statement: str) -> str:
    return statement.replace("?", "%s")


class Database:
    def __init__(self, settings: dict[str, object], pool: Any | None = None):
        self.pool = pool or pooling.MySQLConnectionPool(
            pool_name="vietincare_python",
            pool_size=10,
            pool_reset_session=True,
            **settings,
        )

    @contextmanager
    def connection(self) -> Iterator[Any]:
        connection = self.pool.get_connection()
        try:
            cursor = connection.cursor()
            try:
                cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_0900_ai_ci")
                cursor.execute("SET SESSION time_zone = '+00:00'")
            finally:
                cursor.close()
            yield connection
        finally:
            connection.close()

    def fetch_all(self, statement: str, parameters: tuple[object, ...] = ()) -> list[dict[str, Any]]:
        with self.connection() as connection:
            cursor = connection.cursor(dictionary=True, buffered=True)
            try:
                cursor.execute(_sql(statement), parameters)
                return cursor.fetchall()
            finally:
                cursor.close()

    def fetch_one(self, statement: str, parameters: tuple[object, ...] = ()) -> dict[str, Any] | None:
        rows = self.fetch_all(statement, parameters)
        return rows[0] if rows else None

    def execute(self, statement: str, parameters: tuple[object, ...] = ()) -> int:
        with self.connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.execute(_sql(statement), parameters)
                connection.commit()
                return int(cursor.lastrowid)
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()

    @contextmanager
    def transaction(self) -> Iterator["Transaction"]:
        with self.connection() as connection:
            connection.start_transaction()
            transaction = Transaction(connection)
            try:
                yield transaction
                connection.commit()
            except Exception:
                connection.rollback()
                raise


class Transaction:
    def __init__(self, connection: Any):
        self.connection = connection

    def fetch_all(self, statement: str, parameters: tuple[object, ...] = ()) -> list[dict[str, Any]]:
        cursor = self.connection.cursor(dictionary=True, buffered=True)
        try:
            cursor.execute(_sql(statement), parameters)
            return cursor.fetchall()
        finally:
            cursor.close()

    def fetch_one(self, statement: str, parameters: tuple[object, ...] = ()) -> dict[str, Any] | None:
        rows = self.fetch_all(statement, parameters)
        return rows[0] if rows else None

    def execute(self, statement: str, parameters: tuple[object, ...] = ()) -> int:
        cursor = self.connection.cursor()
        try:
            cursor.execute(_sql(statement), parameters)
            return int(cursor.lastrowid)
        finally:
            cursor.close()