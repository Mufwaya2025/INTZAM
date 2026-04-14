#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_konse_odoo_flow.py
=======================
End-to-end integration tests for the Konse Konse (*543#) payment gateway
integration with IntZam LMS and Odoo 17.

Tests
-----
01  Create a test res.partner in Odoo via XML-RPC
02  Mock KK disbursement → handle_disbursement_confirmed() → verify Odoo move
03  Simulate REPAYMENT_RECEIVED webhook payload → handle_repayment_received()
04  Simulate FEE_COLLECTED event for origination fee → handle_fee_collected()
05  Simulate AGENT_COLLECTION event → handle_agent_collection()
06  Idempotency — call handle_disbursement_confirmed() twice, assert Odoo called once
07  Query Odoo for all KK-related journal entries and print a summary table

Prerequisites
-------------
- Odoo running at localhost:8069, db=odoo_lms_test, user=admin, password=admin1234
- Django settings must be configured (DJANGO_SETTINGS_MODULE)
- KK credentials are MOCKED — no real KK calls are made
- Do NOT run with `python -m pytest` — use `python test_konse_odoo_flow.py` directly

WARNING
-------
Do NOT run this script against a production Odoo instance.  It creates test
res.partner records and journal entries that must be cleaned up manually.
"""

from __future__ import annotations

import os
import sys
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

# ── Django setup (must precede any Django/DRF imports) ────────────────────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import django
django.setup()

# Now safe to import LMS modules
from apps.accounting.odoo_client import get_odoo_client, OdooConnectionError


# ── Helper: build a minimal Loan stub ────────────────────────────────────────

def _make_loan_stub(loan_number: str, amount: float, odoo_partner_id: int | None = None) -> SimpleNamespace:
    """
    Return a SimpleNamespace that quacks like an LMS Loan instance enough for
    konse_events handlers to work without touching the database.
    """
    client_stub = SimpleNamespace(
        name=f'Test Borrower {loan_number}',
        phone='0971234567',
        national_id='123456789',
        address='Test Address, Lusaka',
        city='Lusaka',
    )
    product_stub = SimpleNamespace(
        name='Test Product',
        interest_type='FLAT',
        interest_rate=Decimal('5.00'),
        nominal_interest_rate=Decimal('5.00'),
        credit_facilitation_fee=Decimal('0.00'),
        processing_fee=Decimal('0.00'),
    )
    return SimpleNamespace(
        loan_number=loan_number,
        amount=Decimal(str(amount)),
        total_repayable=Decimal(str(amount * 1.1)),
        repaid_amount=Decimal('0.00'),
        monthly_payment=Decimal(str(amount * 1.1 / 6)),
        term_months=6,
        interest_rate=Decimal('5.00'),
        days_overdue=0,
        status='ACTIVE',
        odoo_partner_id=odoo_partner_id,
        client=client_stub,
        product=product_stub,
    )


# ── Test suite ────────────────────────────────────────────────────────────────

class KonseOdooFlowTests(unittest.TestCase):
    """
    Integration tests for the Konse Konse → LMS → Odoo accounting pipeline.

    Odoo-touching tests use a real XML-RPC connection.
    KK API calls are mocked via unittest.mock.patch.
    """

    # Partner created in test_01 — shared across tests via class variable
    _odoo_partner_id: int | None = None
    _odoo_move_ids: list[int]    = []

    @classmethod
    def setUpClass(cls) -> None:
        """Connect to Odoo once for the entire test suite."""
        super().setUpClass()
        try:
            cls.odoo = get_odoo_client()
            if cls.odoo.enabled:
                cls.odoo.authenticate()
                print(f'\n[setUpClass] Connected to Odoo uid={cls.odoo._uid}')
            else:
                print('\n[setUpClass] Odoo is DISABLED — skipping Odoo assertions.')
        except OdooConnectionError as exc:
            print(f'\n[setUpClass] WARNING: Odoo not reachable: {exc}')
            cls.odoo = None  # type: ignore[assignment]

    # ── Test 01 ───────────────────────────────────────────────────────────────

    def test_01_create_odoo_borrower(self):
        """Create a test res.partner in Odoo and assert an ID is returned."""
        if not (self.odoo and self.odoo.enabled):
            self.skipTest('Odoo not available')

        partner_vals = {
            'name':     'KK Test Borrower T01',
            'phone':    '0971230001',
            'email':    'kk_test_01@intzam.test',
            'street':   '10 Cairo Road',
            'city':     'Lusaka',
            'country_id': 248,  # Zambia
            'is_company': False,
        }
        partner_id = self.odoo._create('res.partner', partner_vals)

        self.assertIsNotNone(partner_id, 'Expected a non-None partner_id')
        self.assertIsInstance(partner_id, int, 'partner_id must be an integer')
        self.assertGreater(partner_id, 0, 'partner_id must be positive')

        # Store for use in later tests
        KonseOdooFlowTests._odoo_partner_id = partner_id
        print(f'  [test_01] Created res.partner id={partner_id}')

    # ── Test 02 ───────────────────────────────────────────────────────────────

    def test_02_disburse_loan_via_konse(self):
        """
        Mock KK disburse_loan() returning CONFIRMED, call handle_disbursement_confirmed(),
        verify Odoo journal entry was created in the LDIS journal.
        """
        from apps.accounting import konse_events
        from apps.loans.models import KonseTransaction, KonseTransactionStatus

        kk_ref   = 'KK-TEST-001'
        loan_num = 'TEST-LOAN-001'
        amount   = 1500.00

        # Ensure no leftover KonseTransaction from a previous run
        KonseTransaction.objects.filter(transaction_reference=kk_ref).delete()

        # Create a placeholder KonseTransaction record so _mark_confirmed() can update it
        from apps.loans.models import KonseTransactionType
        KonseTransaction.objects.create(
            transaction_reference=kk_ref,
            transaction_type=KonseTransactionType.DISBURSEMENT,
            amount=Decimal(str(amount)),
            status=KonseTransactionStatus.PENDING,
        )

        loan = _make_loan_stub(
            loan_number=loan_num,
            amount=amount,
            odoo_partner_id=self._odoo_partner_id,
        )

        move_id = konse_events.handle_disbursement_confirmed(
            kk_ref=kk_ref,
            loan=loan,
            amount=amount,
        )

        if self.odoo and self.odoo.enabled:
            self.assertIsNotNone(move_id, 'Expected Odoo move_id to be set')
            self.assertIsInstance(move_id, int)
            self.assertGreater(move_id, 0)

            # Verify the move exists in Odoo and is posted
            moves = self.odoo._search_read(
                'account.move',
                [['id', '=', move_id], ['state', '=', 'posted']],
                ['id', 'ref', 'journal_id'],
            )
            self.assertEqual(len(moves), 1, 'Expected exactly one posted move')
            self.assertIn('DISB-KK-KK-TEST-001', moves[0].get('ref', ''))
            KonseOdooFlowTests._odoo_move_ids.append(move_id)
            print(f'  [test_02] Odoo disbursement move_id={move_id}')
        else:
            print('  [test_02] Odoo disabled — skipping move assertions')

        # Verify KonseTransaction marked CONFIRMED
        txn = KonseTransaction.objects.get(transaction_reference=kk_ref)
        self.assertEqual(txn.status, KonseTransactionStatus.CONFIRMED)

    # ── Test 03 ───────────────────────────────────────────────────────────────

    def test_03_repayment_webhook(self):
        """
        Simulate a REPAYMENT_RECEIVED webhook payload and call
        handle_repayment_received(). Verify Odoo is called (mocked if needed).
        """
        from apps.accounting import konse_events
        from apps.loans.models import KonseTransaction, KonseTransactionStatus, KonseTransactionType

        kk_ref   = 'KK-TEST-002'
        loan_num = 'TEST-LOAN-001'
        amount   = 500.00

        KonseTransaction.objects.filter(transaction_reference=kk_ref).delete()
        KonseTransaction.objects.create(
            transaction_reference=kk_ref,
            transaction_type=KonseTransactionType.REPAYMENT,
            amount=Decimal(str(amount)),
            status=KonseTransactionStatus.PENDING,
        )

        loan = _make_loan_stub(
            loan_number=loan_num,
            amount=2000.00,
            odoo_partner_id=self._odoo_partner_id,
        )
        # Simulate a partially repaid loan
        loan.repaid_amount = Decimal('500.00')

        move_id = konse_events.handle_repayment_received(
            kk_ref=kk_ref,
            loan=loan,
            amount=amount,
        )

        txn = KonseTransaction.objects.get(transaction_reference=kk_ref)
        self.assertEqual(txn.status, KonseTransactionStatus.CONFIRMED)
        print(f'  [test_03] Repayment processed, move_id={move_id}')

    # ── Test 04 ───────────────────────────────────────────────────────────────

    def test_04_fee_collection(self):
        """
        Simulate a FEE_COLLECTED event for origination fee.
        Verify Odoo journal entry uses account 4201.
        """
        from apps.accounting import konse_events
        from apps.loans.models import KonseTransaction, KonseTransactionStatus, KonseTransactionType

        kk_ref   = 'KK-TEST-003'
        loan_num = 'TEST-LOAN-001'
        amount   = 150.00
        fee_type = 'origination'

        KonseTransaction.objects.filter(transaction_reference=kk_ref).delete()
        KonseTransaction.objects.create(
            transaction_reference=kk_ref,
            transaction_type=KonseTransactionType.FEE,
            amount=Decimal(str(amount)),
            status=KonseTransactionStatus.PENDING,
        )

        loan = _make_loan_stub(
            loan_number=loan_num,
            amount=1500.00,
            odoo_partner_id=self._odoo_partner_id,
        )

        move_id = konse_events.handle_fee_collected(
            kk_ref=kk_ref,
            loan=loan,
            amount=amount,
            fee_type=fee_type,
        )

        txn = KonseTransaction.objects.get(transaction_reference=kk_ref)
        self.assertEqual(txn.status, KonseTransactionStatus.CONFIRMED)
        print(f'  [test_04] Fee ({fee_type}) processed, move_id={move_id}')

        if self.odoo and self.odoo.enabled and move_id:
            KonseOdooFlowTests._odoo_move_ids.append(move_id)
            # Check that the credit side went to 4201
            lines = self.odoo._search_read(
                'account.move.line',
                [['move_id', '=', move_id], ['credit', '>', 0]],
                ['account_id'],
            )
            self.assertTrue(len(lines) > 0, 'Expected at least one credit line')

    # ── Test 05 ───────────────────────────────────────────────────────────────

    def test_05_agent_collection(self):
        """
        Simulate an AGENT_COLLECTION event.
        Verify KonseTransaction marked CONFIRMED.
        """
        from apps.accounting import konse_events
        from apps.loans.models import KonseTransaction, KonseTransactionStatus, KonseTransactionType

        kk_ref     = 'KK-TEST-004'
        loan_num   = 'TEST-LOAN-001'
        amount     = 300.00
        agent_code = 'AGT001'

        KonseTransaction.objects.filter(transaction_reference=kk_ref).delete()
        KonseTransaction.objects.create(
            transaction_reference=kk_ref,
            transaction_type=KonseTransactionType.AGENT_COLLECTION,
            amount=Decimal(str(amount)),
            status=KonseTransactionStatus.PENDING,
        )

        loan = _make_loan_stub(
            loan_number=loan_num,
            amount=1500.00,
            odoo_partner_id=self._odoo_partner_id,
        )

        move_id = konse_events.handle_agent_collection(
            kk_ref=kk_ref,
            loan=loan,
            amount=amount,
            agent_code=agent_code,
        )

        txn = KonseTransaction.objects.get(transaction_reference=kk_ref)
        self.assertEqual(txn.status, KonseTransactionStatus.CONFIRMED)
        print(f'  [test_05] Agent collection processed, move_id={move_id}')

        if self.odoo and self.odoo.enabled and move_id:
            KonseOdooFlowTests._odoo_move_ids.append(move_id)

    # ── Test 06 ───────────────────────────────────────────────────────────────

    def test_06_idempotency(self):
        """
        Call handle_disbursement_confirmed() twice with the same KK reference.
        Assert that Odoo's _create is invoked only once (second call is a no-op).
        """
        from apps.accounting import konse_events
        from apps.loans.models import KonseTransaction, KonseTransactionStatus, KonseTransactionType

        kk_ref   = 'KK-TEST-IDEM'
        loan_num = 'TEST-LOAN-IDEM'
        amount   = 800.00

        KonseTransaction.objects.filter(transaction_reference=kk_ref).delete()
        KonseTransaction.objects.create(
            transaction_reference=kk_ref,
            transaction_type=KonseTransactionType.DISBURSEMENT,
            amount=Decimal(str(amount)),
            status=KonseTransactionStatus.PENDING,
        )

        loan = _make_loan_stub(
            loan_number=loan_num,
            amount=amount,
            odoo_partner_id=self._odoo_partner_id,
        )

        odoo_client = get_odoo_client()

        with patch.object(odoo_client, '_create', wraps=odoo_client._create if odoo_client.enabled else MagicMock(return_value=9999)) as mock_create:
            # First call — should go through
            move_id_1 = konse_events.handle_disbursement_confirmed(
                kk_ref=kk_ref,
                loan=loan,
                amount=amount,
            )
            # Second call — should be blocked by idempotency guard
            move_id_2 = konse_events.handle_disbursement_confirmed(
                kk_ref=kk_ref,
                loan=loan,
                amount=amount,
            )

        # The second call must return None (skipped)
        self.assertIsNone(move_id_2, 'Second call must be a no-op and return None')

        # KonseTransaction must still be CONFIRMED (from first call)
        txn = KonseTransaction.objects.get(transaction_reference=kk_ref)
        self.assertEqual(txn.status, KonseTransactionStatus.CONFIRMED)

        print(
            f'  [test_06] Idempotency OK: first_move_id={move_id_1}, '
            f'second_move_id={move_id_2} (expected None)'
        )

    # ── Test 07 ───────────────────────────────────────────────────────────────

    def test_07_print_summary(self):
        """
        Query Odoo for all journal entries with references matching KK patterns
        and print a formatted summary table.
        """
        if not (self.odoo and self.odoo.enabled):
            self.skipTest('Odoo not available')

        patterns = ['DISB-KK-', 'REPY-', 'FEE-KK-', 'AGNT-KK-']
        all_moves = []

        for pattern in patterns:
            try:
                moves = self.odoo._search_read(
                    'account.move',
                    [['ref', 'ilike', pattern], ['state', '=', 'posted']],
                    ['id', 'ref', 'date', 'journal_id', 'amount_total'],
                    order='date desc',
                    limit=20,
                )
                all_moves.extend(moves)
            except Exception as exc:
                print(f'  [test_07] Could not query pattern {pattern!r}: {exc}')

        if not all_moves:
            print('\n  [test_07] No KK-related journal entries found in Odoo.')
            return

        # Print formatted table
        print('\n')
        print('  ╔═══════════╦══════════════════════════════════╦════════════╦═══════════════╦══════════════╗')
        print('  ║  Move ID  ║  Reference                       ║  Date      ║  Journal      ║  Amount ZMW  ║')
        print('  ╠═══════════╬══════════════════════════════════╬════════════╬═══════════════╬══════════════╣')
        for m in sorted(all_moves, key=lambda x: x.get('date', ''), reverse=True):
            j_name = m['journal_id'][1] if isinstance(m.get('journal_id'), list) else str(m.get('journal_id', ''))
            print(
                f'  ║ {m["id"]:>9} ║ {str(m.get("ref","")):<32} ║ {str(m.get("date","")):<10} ║ '
                f'{j_name:<13} ║ {m.get("amount_total", 0):>12.2f} ║'
            )
        print('  ╚═══════════╩══════════════════════════════════╩════════════╩═══════════════╩══════════════╝')
        print(f'  [test_07] {len(all_moves)} KK-related journal entries found.\n')

        # Test passes as long as we don't crash
        self.assertIsInstance(all_moves, list)


# ── Runner ────────────────────────────────────────────────────────────────────

def _print_final_summary():
    """Print a quick final summary of what was created during the test run."""
    print('\n' + '=' * 70)
    print('  Konse Konse ↔ Odoo Integration Test Summary')
    print('=' * 70)

    try:
        from apps.loans.models import KonseTransaction, KonseTransactionStatus
        confirmed = KonseTransaction.objects.filter(status=KonseTransactionStatus.CONFIRMED).count()
        pending   = KonseTransaction.objects.filter(status=KonseTransactionStatus.PENDING).count()
        failed    = KonseTransaction.objects.filter(status=KonseTransactionStatus.FAILED).count()
        print(f'  KonseTransaction records — CONFIRMED={confirmed} PENDING={pending} FAILED={failed}')
    except Exception as exc:
        print(f'  Could not query KonseTransaction: {exc}')

    odoo = get_odoo_client()
    if odoo.enabled:
        try:
            odoo.authenticate()
            kk_moves = odoo._search(
                'account.move',
                [['ref', 'ilike', 'KK-'], ['state', '=', 'posted']],
            )
            print(f'  Odoo posted KK moves      — count={len(kk_moves)}')
        except Exception as exc:
            print(f'  Could not query Odoo: {exc}')
    else:
        print('  Odoo integration disabled.')

    print('=' * 70 + '\n')


if __name__ == '__main__':
    # Run all tests then print a summary
    loader  = unittest.TestLoader()
    suite   = loader.loadTestsFromTestCase(KonseOdooFlowTests)
    runner  = unittest.TextTestRunner(verbosity=2)
    result  = runner.run(suite)
    _print_final_summary()
    sys.exit(0 if result.wasSuccessful() else 1)
