import os

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

_conn = psycopg2.connect(DATABASE_URL)
_conn.autocommit = True


def get_cursor():
    return _conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
