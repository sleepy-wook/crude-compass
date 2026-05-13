"""Lakebase Postgres repositories — typed CRUD per domain entity.

Pattern: each repository file (missions.py, decisions.py, ...) defines
async functions that take a `psycopg.Connection` and return Pydantic models.

DDL lives in `databricks/schemas/lakebase.sql`.
"""
