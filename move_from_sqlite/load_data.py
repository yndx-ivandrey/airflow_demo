import os
import pathlib
import sqlite3
from contextlib import contextmanager
import psycopg2
from db_settings import DSL
from psycopg2.extras import DictCursor
from transfer_to_psql import PostgresSaver, SQLiteLoader


def dict_factory(curs: sqlite3.Cursor, row: tuple) -> dict:
    d = {}
    for idx, col in enumerate(curs.description):
        d[col[0]] = row[idx]
    return d


@contextmanager
def connection_context(db_path: str):
    connection = sqlite3.connect(db_path)
    connection.row_factory = dict_factory
    yield connection
    connection.close()


def load_from_sqlite(
    connection: sqlite3.Connection, pg_conn: DictCursor
) -> None:
    postgres_saver = PostgresSaver(pg_conn)

    sqlite_loader = SQLiteLoader(connection)

    data = sqlite_loader.load_movies()
    postgres_saver.save_all_data(data)


if __name__ == '__main__':

    db = os.path.join(pathlib.Path(__file__).parent.absolute(), 'db.sqlite')
    schema_file = os.path.join(
        pathlib.Path(__file__).parent.absolute(), 'content_schema.sql'
    )

    with connection_context(db) as sql_connect, psycopg2.connect(
        **DSL
    ) as conn, conn.cursor() as cursor:
        cursor.execute(open(schema_file, 'r').read())
        load_from_sqlite(sql_connect, cursor)
