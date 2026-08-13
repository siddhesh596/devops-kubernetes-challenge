"""
Database access layer.

Wraps psycopg2 connections and holds all raw SQL used by the application.
No secrets are ever logged from this module.
"""

import logging

import psycopg2
import psycopg2.extras

from config import Config

logger = logging.getLogger(__name__)

CREATE_TASKS_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_connection():
    """Open a new database connection using configured environment variables."""
    return psycopg2.connect(**Config.db_connection_kwargs())


def init_db():
    """Create the tasks table if it does not already exist.

    Called on application startup so that no manual SQL steps are required.
    """
    try:
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(CREATE_TASKS_TABLE)
            conn.commit()
            logger.info("Database schema is ready")
        finally:
            conn.close()
    except psycopg2.Error:
        # Do not crash app startup just because the DB isn't ready yet;
        # /db-health will report the outage and callers can retry.
        logger.error("Failed to initialize database schema", exc_info=True)


def check_connection():
    """Return True if a connection to PostgreSQL can be established."""
    try:
        conn = get_connection()
        conn.close()
        return True
    except psycopg2.Error:
        logger.error("Database connectivity check failed", exc_info=True)
        return False


def fetch_all_tasks():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, title, description, status FROM tasks ORDER BY id;"
            )
            return cur.fetchall()
    finally:
        conn.close()


def fetch_task(task_id):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, title, description, status FROM tasks WHERE id = %s;",
                (task_id,),
            )
            return cur.fetchone()
    finally:
        conn.close()


def create_task(title, description, status):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO tasks (title, description, status)
                VALUES (%s, %s, %s)
                RETURNING id, title, description, status;
                """,
                (title, description, status),
            )
            row = cur.fetchone()
        conn.commit()
        return row
    finally:
        conn.close()


def update_task(task_id, title, description, status):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                UPDATE tasks
                SET title = %s, description = %s, status = %s
                WHERE id = %s
                RETURNING id, title, description, status;
                """,
                (title, description, status, task_id),
            )
            row = cur.fetchone()
        conn.commit()
        return row
    finally:
        conn.close()


def delete_task(task_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s RETURNING id;", (task_id,))
            row = cur.fetchone()
        conn.commit()
        return row is not None
    finally:
        conn.close()
