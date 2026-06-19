"""
API integration tests for Moliyachi backend.
Uses FastAPI TestClient with an isolated temp SQLite database.
"""
import sys
import os
import tempfile
import pathlib
import pytest
from fastapi.testclient import TestClient

# Make backend importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Redirect DB to a temp file BEFORE importing main so every function
# in database.py picks up the new DB_PATH from its module globals.
_tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp.close()
import database
database.DB_PATH = pathlib.Path(_tmp.name)

from main import app   # noqa: E402  (must come after DB patch)

TEST_USER = 99999
ALT_USER  = 88888


# ── Session fixture: start app (triggers startup → init_db) ───────────────
@pytest.fixture(scope='module')
def client():
    with TestClient(app) as c:
        yield c


# ── Helper ────────────────────────────────────────────────────────────────
def add_tx(client, amount, type_, category, description=None, user_id=TEST_USER):
    return client.post('/api/transaction', json={
        'user_id': user_id,
        'amount': amount,
        'type': type_,
        'category': category,
        'description': description,
    })


# ══════════════════════════════════════════════════════════
# STATIC / HTML
# ══════════════════════════════════════════════════════════
def test_serve_frontend(client):
    r = client.get('/')
    assert r.status_code == 200
    assert 'text/html' in r.headers['content-type']


def test_static_css(client):
    r = client.get('/static/style.css')
    assert r.status_code == 200


def test_static_js(client):
    r = client.get('/static/app.js')
    assert r.status_code == 200


# ══════════════════════════════════════════════════════════
# TRANSACTIONS — add
# ══════════════════════════════════════════════════════════
def test_add_expense(client):
    r = add_tx(client, 50_000, 'expense', 'Oziq-ovqat', 'Non va yog')
    assert r.status_code == 200
    assert r.json()['success'] is True


def test_add_income(client):
    r = add_tx(client, 3_000_000, 'income', 'Maosh')
    assert r.status_code == 200
    assert r.json()['success'] is True


def test_add_tx_missing_fields(client):
    r = client.post('/api/transaction', json={'user_id': TEST_USER})
    assert r.status_code == 422          # FastAPI validation error


def test_add_tx_negative_treated_as_positive(client):
    r = add_tx(client, -10_000, 'expense', 'Transport')
    assert r.status_code == 200          # backend calls abs()


# ══════════════════════════════════════════════════════════
# TRANSACTIONS — list
# ══════════════════════════════════════════════════════════
def test_get_transactions_returns_list(client):
    r = client.get(f'/api/transactions/{TEST_USER}')
    assert r.status_code == 200
    body = r.json()
    assert 'transactions' in body
    assert isinstance(body['transactions'], list)
    assert len(body['transactions']) >= 2


def test_get_transactions_limit(client):
    for i in range(5):
        add_tx(client, 1000 * (i + 1), 'expense', 'Boshqa')
    r = client.get(f'/api/transactions/{TEST_USER}?limit=3')
    assert r.status_code == 200
    assert len(r.json()['transactions']) <= 3


def test_get_transactions_unknown_user(client):
    r = client.get('/api/transactions/0')
    assert r.status_code == 200
    assert r.json()['transactions'] == []


# ══════════════════════════════════════════════════════════
# BALANCE
# ══════════════════════════════════════════════════════════
def test_balance_fields(client):
    r = client.get(f'/api/balance/{TEST_USER}')
    assert r.status_code == 200
    body = r.json()
    for key in ('balance', 'total_income', 'total_expense', 'user_id'):
        assert key in body


def test_balance_calculation(client):
    client.post('/api/transaction', json={
        'user_id': ALT_USER, 'amount': 1_000_000,
        'type': 'income', 'category': 'Maosh',
    })
    client.post('/api/transaction', json={
        'user_id': ALT_USER, 'amount': 200_000,
        'type': 'expense', 'category': 'Kommunal',
    })
    r = client.get(f'/api/balance/{ALT_USER}')
    body = r.json()
    assert body['total_income']  == pytest.approx(1_000_000)
    assert body['total_expense'] == pytest.approx(200_000)
    assert body['balance']       == pytest.approx(800_000)


def test_balance_zero_for_unknown_user(client):
    r = client.get('/api/balance/77777')
    body = r.json()
    assert body['balance']       == 0
    assert body['total_income']  == 0
    assert body['total_expense'] == 0


# ══════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════
def test_report_shape(client):
    r = client.get(f'/api/report/{TEST_USER}')
    assert r.status_code == 200
    body = r.json()
    for key in ('income_total', 'expense_total', 'net',
                'month_name', 'income_by_category', 'expense_by_category'):
        assert key in body


def test_report_net_equals_income_minus_expense(client):
    r = client.get(f'/api/report/{TEST_USER}')
    body = r.json()
    assert body['net'] == pytest.approx(body['income_total'] - body['expense_total'])


def test_report_categories_are_lists(client):
    r = client.get(f'/api/report/{TEST_USER}')
    body = r.json()
    assert isinstance(body['income_by_category'],  list)
    assert isinstance(body['expense_by_category'], list)


def test_report_unknown_user_is_zero(client):
    r = client.get('/api/report/66666')
    body = r.json()
    assert body['income_total']  == 0
    assert body['expense_total'] == 0
    assert body['net']           == 0


def test_report_month_name_is_string(client):
    r = client.get(f'/api/report/{TEST_USER}')
    assert isinstance(r.json()['month_name'], str)
    assert len(r.json()['month_name']) > 0


# ══════════════════════════════════════════════════════════
# DELETE (clear all data)
# ══════════════════════════════════════════════════════════
def test_delete_transactions(client):
    uid = 55555
    client.post('/api/transaction', json={
        'user_id': uid, 'amount': 500_000,
        'type': 'income', 'category': 'Freelance',
    })
    before = client.get(f'/api/transactions/{uid}').json()
    assert len(before['transactions']) > 0

    r = client.delete(f'/api/transactions/{uid}')
    assert r.status_code == 200
    body = r.json()
    assert body['success'] is True
    assert body['deleted'] >= 1

    after = client.get(f'/api/balance/{uid}').json()
    assert after['balance'] == 0


def test_delete_unknown_user_returns_zero(client):
    r = client.delete('/api/transactions/44444')
    assert r.status_code == 200
    assert r.json()['deleted'] == 0


# ══════════════════════════════════════════════════════════
# CURRENCY
# ══════════════════════════════════════════════════════════
def test_currency_endpoint_shape(client):
    r = client.get('/api/currency')
    assert r.status_code == 200
    body = r.json()
    assert 'rates' in body
    assert isinstance(body['rates'], dict)
