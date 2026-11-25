"""Database URL handling for local PostgreSQL and Supabase (no network). Example hosts/credentials are placeholders."""

from app.database.session import connect_args_for, is_supabase, normalize_database_url


def test_local_url_unchanged():
    url = "postgresql+psycopg://reprocare:reprocare@localhost:5432/reprocare"
    assert normalize_database_url(url) == url
    assert connect_args_for(url) == {}


def test_supabase_direct_and_session_pooler():
    direct = normalize_database_url("postgresql://postgres:PLACEHOLDER@db.abcdefghijklmnop.supabase.co:5432/postgres")
    assert direct.startswith("postgresql+psycopg://") and direct.endswith("sslmode=require")
    session = normalize_database_url("postgres://postgres.abcdefghijklmnop:PLACEHOLDER@aws-0-eu-central-1.pooler.supabase.com:5432/postgres")
    assert is_supabase(session) and "sslmode=require" in session and connect_args_for(session) == {}


def test_supabase_transaction_pooler_disables_prepared_statements():
    url = normalize_database_url("postgresql://postgres.abc:PLACEHOLDER@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?sslmode=verify-full")
    assert "sslmode=verify-full" in url and "sslmode=require" not in url  # an explicit choice is kept
    assert connect_args_for(url) == {"prepare_threshold": None}


def test_password_with_special_characters_is_preserved():
    url = normalize_database_url("postgresql://postgres:p%40ss%2Fw0rd@db.abc.supabase.co:5432/postgres")
    assert "p%40ss%2Fw0rd@" in url


def test_shared_database_guard_refuses_other_databases(monkeypatch):
    import pytest
    from app.database.session import require_shared_database

    supabase = "postgresql+psycopg://rc_tester.abcdefghijkl:pw@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
    monkeypatch.delenv("REPROCARE_REQUIRE_SHARED_DATABASE", raising=False)
    assert require_shared_database("postgresql+psycopg://me@localhost:5432/local", lambda: "me") is None  # not requested: unchanged
    monkeypatch.setenv("REPROCARE_REQUIRE_SHARED_DATABASE", "true")
    with pytest.raises(RuntimeError, match="not the shared Supabase database") as refused:
        require_shared_database("postgresql+psycopg://me:secret@localhost:5432/local", lambda: "me")
    assert "secret" not in str(refused.value) and "localhost" not in str(refused.value)
    with pytest.raises(RuntimeError, match="expected login"):
        require_shared_database(supabase, lambda: "postgres")
    assert require_shared_database(supabase, lambda: "rc_tester") == "rc_tester"


def test_backend_does_not_start_when_the_shared_database_is_required_but_missing(monkeypatch):
    import pytest
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setenv("REPROCARE_REQUIRE_SHARED_DATABASE", "true")
    with pytest.raises(RuntimeError, match="not the shared Supabase database"):
        with TestClient(app):
            pass
