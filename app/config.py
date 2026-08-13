"""
Application configuration.

All configuration is read from environment variables so that the exact
same Docker image can be promoted from local development, to Docker,
to Kubernetes, to production without any code changes.
"""

import os


class Config:
    """Central configuration object, populated from environment variables."""

    # --- Application ---
    APP_NAME = "DevOps Kubernetes Challenge API"
    APP_VERSION = "1.0.0"

    # --- Database ---
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "5432")
    DB_NAME = os.environ.get("DB_NAME", "appdb")
    DB_USER = os.environ.get("DB_USER", "postgres")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")

    @classmethod
    def db_connection_kwargs(cls):
        """Return connection kwargs for psycopg2, never logged or exposed."""
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "dbname": cls.DB_NAME,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
        }
