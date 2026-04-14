# -*- coding: utf-8 -*-
"""
konse_events.py
===============
Routes confirmed Konse Konse (*543#) payment events to Odoo 17 accounting.

Each handler in this module corresponds to a Konse Konse event type:

  DISBURSEMENT_CONFIRMED  → handle_disbursement_confirmed()
  REPAYMENT_RECEIVED      → handle_repayment_received()
  FEE_COLLECTED           → handle_fee_collected()
  AGENT_COLLECTION        → handle_agent_collection()

Accounting logic (COA codes used)
----------------------------------
KK Gateway Float         1107  (asset_cash    — funds in transit via KK)
KK Disbursement Clearing 1108  (asset_current — pending disbursement staging)
Loan Receivable S1       1111
Bank Main Clearing       1105
Origination Fee Income   4201
Application Fee Income   4203
Agent Commission Income  4205
KK Fees Payable          2111  (not used in these event handlers directly)

NOTE: Account codes 1106 (Bank USD Account) and 2110 (Lease Liability Current)
already exist in this Odoo instance and cannot be reused.  Konse Konse float
accounts are therefore 1107/1108/2111/5223 instead of the original guide's
1106/2110 suggestion.

Disbursement journal entry sequence
-------------------------------------
On KK DISBURSEMENT_CONFIRMED two journal lines are created in one move:
  Dr 1107 KK Gateway Float       (funds now in KK transit account)
  Cr 1108 KK Disbursement Clearing (clears the staging entry from approval)

Then settlement move (same posting call, two-step narration):
  Dr 1111 Loan Receivable S1     (create the receivable on the books)
  Cr 1107 KK Gateway Float       (KK has delivered to borrower's wallet)

Idempotency
-----------
All handlers guard against duplicate processing by:
1. Checking ``KonseTransaction.status == CONFIRMED`` for this reference.
2. Checking Odoo for a journal entry with lms_reference = the canonical ref
   (e.g. 'DISB-KK-{kk_ref}').

Error policy
------------
Odoo errors are caught, logged, and NOT re-raised.  The LMS database record
(KonseTransaction) is committed before calling these handlers, so failing the
Odoo sync must not roll back the LMS state.  A scheduled reconciliation job
will retry any Odoo-missed entries.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from apps.accounting.odoo_client import (
    OdooConnectionError,
    OdooDuplicateError,
    OdooPostingError,
    get_odoo_client,
)
from apps.accounting.on_payment_received import on_payment_received
from apps.loans.models import KonseTransaction, KonseTransactionStatus

_logger = logging.getLogger(__name__)


# ── Internal helpers ───────────────────────────────────────────────────────────

def _today(move_date: str | None) -> str:
    """Return move_date if given, otherwise today's ISO date string."""
    return move_date or str(date.today())


def _is_already_confirmed(kk_ref: str) -> bool:
    """
    Return True if a KonseTransaction with this reference is already CONFIRMED.

    This is the first idempotency gate — avoids even touching Odoo when the
    LMS record already shows the event was fully processed.
    """
    return KonseTransaction.objects.filter(
        transaction_reference=kk_ref,
        status=KonseTransactionStatus.CONFIRMED,
    ).exists()


def _mark_confirmed(kk_ref: str, odoo_move_id: int | None) -> None:
    """
    Update the KonseTransaction record to CONFIRMED and store the Odoo move ID.

    No-op if the record does not exist (e.g. webhook-less flow where the
    transaction was created by the poller without a DB record yet).
    """
    from django.utils import timezone

    KonseTransaction.objects.filter(
        transaction_reference=kk_ref,
    ).update(
        status=KonseTransactionStatus.CONFIRMED,
        odoo_move_id=odoo_move_id,
        processed_at=timezone.now(),
    )


# ── Public event handlers ──────────────────────────────────────────────────────

def handle_disbursement_confirmed(
    kk_ref: str,
    loan: Any,
    amount: float,
    move_date: str | None = None,
) -> int | None:
    """
    Post Odoo journal entries when a KK disbursement is confirmed.

    Two-step accounting move posted as one Odoo account.move:

      Step 1 — Clear the pending disbursement staging:
        Dr 1107 KK Gateway Float
        Cr 1108 KK Disbursement Clearing

      Step 2 — Settle to the loan receivable:
        Dr 1111 Loan Receivable S1
        Cr 1107 KK Gateway Float

    The combined entry (4 lines) is posted to the LDIS journal with
    lms_reference = 'DISB-KK-{kk_ref}' for idempotency.

    Args:
        kk_ref:    Konse Konse transaction reference string.
        loan:      LMS Loan instance.
        amount:    ZMW amount disbursed.
        move_date: ISO date string; defaults to today.

    Returns:
        Odoo account.move id, or None if Odoo is disabled/errored.
    """
    if _is_already_confirmed(kk_ref):
        _logger.info(
            'handle_disbursement_confirmed: ref=%s already CONFIRMED — skip.',
            kk_ref,
        )
        return None

    lms_ref  = f'DISB-KK-{kk_ref}'
    entry_dt = _today(move_date)
    client   = get_odoo_client()
    move_id: int | None = None

    if not client.enabled:
        _logger.info('[Odoo disabled] Skipping KK disbursement sync for loan %s.', loan.loan_number)
        _mark_confirmed(kk_ref, None)
        return None

    try:
        client.authenticate()

        # Resolve partner
        partner_id: int | None = loan.odoo_partner_id
        if partner_id is None:
            try:
                partner_id = client.sync_borrower(loan.client)
            except (OdooConnectionError, OdooPostingError) as exc:
                _logger.warning(
                    'Could not sync borrower for KK disbursement loan %s: %s',
                    loan.loan_number, exc,
                )

        # Resolve account IDs
        acct_1107 = client._account_id('1107')
        acct_1108 = client._account_id('1108')
        acct_1111 = client._account_id('1111')
        journal_id = client._journal_id('LDIS')

        move_vals = {
            'journal_id': journal_id,
            'date':       entry_dt,
            'ref':        lms_ref,
            'narration':  (
                f'KK Disbursement Confirmed | loan={loan.loan_number} '
                f'amount=ZMW{amount:.2f} kk_ref={kk_ref}'
            ),
            'line_ids': [
                # Step 1: Dr 1107 KK Gateway Float
                (0, 0, {
                    'account_id': acct_1107,
                    'name':       f'KK Gateway Float — DISB {loan.loan_number}',
                    'debit':      float(amount),
                    'credit':     0.0,
                    'partner_id': partner_id,
                }),
                # Step 1: Cr 1108 KK Disbursement Clearing
                (0, 0, {
                    'account_id': acct_1108,
                    'name':       f'KK Disbursement Clearing — DISB {loan.loan_number}',
                    'debit':      0.0,
                    'credit':     float(amount),
                    'partner_id': partner_id,
                }),
                # Step 2: Dr 1111 Loan Receivable S1
                (0, 0, {
                    'account_id': acct_1111,
                    'name':       f'Loan Receivable S1 — {loan.loan_number}',
                    'debit':      float(amount),
                    'credit':     0.0,
                    'partner_id': partner_id,
                }),
                # Step 2: Cr 1107 KK Gateway Float (settled to borrower)
                (0, 0, {
                    'account_id': acct_1107,
                    'name':       f'KK Gateway Float Settlement — {loan.loan_number}',
                    'debit':      0.0,
                    'credit':     float(amount),
                    'partner_id': partner_id,
                }),
            ],
        }

        move_id = client._create('account.move', move_vals)
        client._call('account.move', 'action_post', [[move_id]])

        _logger.info(
            'KK disbursement posted to Odoo: loan=%s kk_ref=%s move_id=%s',
            loan.loan_number, kk_ref, move_id,
        )

    except OdooDuplicateError:
        _logger.warning(
            'KK disbursement entry %r already exists in Odoo for loan %s. Marking confirmed.',
            lms_ref, loan.loan_number,
        )
    except (OdooConnectionError, OdooPostingError) as exc:
        _logger.error(
            'Odoo error in handle_disbursement_confirmed for loan %s ref %s: %s',
            loan.loan_number, kk_ref, exc,
        )
        return None

    _mark_confirmed(kk_ref, move_id)
    return move_id


def handle_repayment_received(
    kk_ref: str,
    loan: Any,
    amount: float,
    move_date: str | None = None,
) -> int | None:
    """
    Post Odoo repayment journal entry when a KK repayment is confirmed.

    Delegates to ``on_payment_received`` (shared with the REST repayment
    endpoint) so the same principal/interest split logic and IFRS 9 stage
    mapping are applied consistently.

    Additionally attempts to find any open Odoo invoice for this loan and
    register the payment against it.

    Args:
        kk_ref:    Konse Konse transaction reference.
        loan:      LMS Loan instance.
        amount:    ZMW amount received.
        move_date: ISO date string; defaults to today.

    Returns:
        Odoo account.move id, or None on failure.
    """
    if _is_already_confirmed(kk_ref):
        _logger.info(
            'handle_repayment_received: ref=%s already CONFIRMED — skip.',
            kk_ref,
        )
        return None

    entry_dt = _today(move_date)
    client   = get_odoo_client()
    move_id: int | None = None

    # Delegate to the shared payment hook — it handles principal/interest split,
    # IFRS 9 staging, and Odoo journal entry creation.
    try:
        move_id = on_payment_received(
            loan=loan,
            amount=amount,
            payment_date=entry_dt,
            transaction_reference=kk_ref,
        )
    except Exception as exc:
        _logger.error(
            'on_payment_received failed for KK ref %s loan %s: %s',
            kk_ref, loan.loan_number, exc,
        )

    # Additionally: reconcile against open Odoo invoice if it exists
    if client.enabled:
        try:
            client.authenticate()
            invoices = client._search_read(
                'account.move',
                [
                    ['ref', 'ilike', loan.loan_number],
                    ['move_type', '=', 'out_invoice'],
                    ['payment_state', 'in', ['not_paid', 'partial']],
                    ['state', '=', 'posted'],
                ],
                ['id', 'amount_residual'],
                limit=1,
                order='invoice_date_due asc',
            )
            if invoices:
                invoice    = invoices[0]
                invoice_id = invoice['id']
                to_pay     = min(float(amount), float(invoice['amount_residual']))
                journal_id = client._journal_id('LRPY')
                partner_id = loan.odoo_partner_id

                payment_vals = {
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'partner_id':   partner_id,
                    'amount':       to_pay,
                    'date':         entry_dt,
                    'journal_id':   journal_id,
                    'ref':          kk_ref,
                    'memo':         f'KK Repayment | {loan.loan_number} | ref={kk_ref}',
                }
                payment_id = client._create('account.payment', payment_vals)
                client._call('account.payment', 'action_post', [[payment_id]])

                # Reconcile payment lines with invoice receivable lines
                pay_lines = client._search_read(
                    'account.move.line',
                    [['payment_id', '=', payment_id],
                     ['account_id.account_type', '=', 'asset_receivable']],
                    ['id'],
                )
                inv_lines = client._search_read(
                    'account.move.line',
                    [['move_id', '=', invoice_id],
                     ['account_id.account_type', '=', 'asset_receivable'],
                     ['reconciled', '=', False]],
                    ['id'],
                )
                if pay_lines and inv_lines:
                    all_ids = [l['id'] for l in pay_lines + inv_lines]
                    client._call('account.move.line', 'reconcile', [all_ids])

                _logger.info(
                    'KK repayment reconciled with invoice %s for loan %s',
                    invoice_id, loan.loan_number,
                )
        except (OdooConnectionError, OdooPostingError) as exc:
            _logger.warning(
                'Could not reconcile KK repayment with Odoo invoice for loan %s: %s',
                loan.loan_number, exc,
            )

    _mark_confirmed(kk_ref, move_id)
    return move_id


def handle_fee_collected(
    kk_ref: str,
    loan: Any,
    amount: float,
    fee_type: str,
    move_date: str | None = None,
) -> int | None:
    """
    Post a fee collection journal entry to Odoo.

    Supported fee types and their income accounts:
      'origination' → 4201 Origination Fee Income
      'application' → 4203 Application Fee Income
      (all others)  → 4203 as default

    Journal entry:
      Dr 1107 KK Gateway Float
      Cr {fee_account} Fee Income

    Idempotency key: 'FEE-KK-{kk_ref}'

    Args:
        kk_ref:    Konse Konse transaction reference.
        loan:      LMS Loan instance.
        amount:    ZMW fee amount collected.
        fee_type:  Fee category string ('origination', 'application', etc.).
        move_date: ISO date string; defaults to today.

    Returns:
        Odoo account.move id, or None on failure.
    """
    if _is_already_confirmed(kk_ref):
        _logger.info(
            'handle_fee_collected: ref=%s already CONFIRMED — skip.',
            kk_ref,
        )
        return None

    _FEE_ACCOUNTS = {
        'origination': '4201',
        'application': '4203',
    }
    fee_account_code = _FEE_ACCOUNTS.get(fee_type.lower(), '4203')
    lms_ref  = f'FEE-KK-{kk_ref}'
    entry_dt = _today(move_date)
    client   = get_odoo_client()
    move_id: int | None = None

    if not client.enabled:
        _logger.info('[Odoo disabled] Skipping KK fee sync for loan %s.', loan.loan_number)
        _mark_confirmed(kk_ref, None)
        return None

    try:
        client.authenticate()

        partner_id: int | None = loan.odoo_partner_id

        acct_1107      = client._account_id('1107')
        acct_fee       = client._account_id(fee_account_code)
        journal_id     = client._journal_id('LFEE')

        move_vals = {
            'journal_id': journal_id,
            'date':       entry_dt,
            'ref':        lms_ref,
            'narration':  (
                f'KK Fee Collected | loan={loan.loan_number} '
                f'fee_type={fee_type} amount=ZMW{amount:.2f} kk_ref={kk_ref}'
            ),
            'line_ids': [
                # Dr 1107 KK Gateway Float
                (0, 0, {
                    'account_id': acct_1107,
                    'name':       f'KK Gateway Float — FEE {fee_type} {loan.loan_number}',
                    'debit':      float(amount),
                    'credit':     0.0,
                    'partner_id': partner_id,
                }),
                # Cr fee income account
                (0, 0, {
                    'account_id': acct_fee,
                    'name':       f'{fee_type.title()} Fee Income — {loan.loan_number}',
                    'debit':      0.0,
                    'credit':     float(amount),
                    'partner_id': partner_id,
                }),
            ],
        }

        move_id = client._create('account.move', move_vals)
        client._call('account.move', 'action_post', [[move_id]])

        _logger.info(
            'KK fee posted to Odoo: loan=%s fee_type=%s kk_ref=%s move_id=%s',
            loan.loan_number, fee_type, kk_ref, move_id,
        )

    except OdooDuplicateError:
        _logger.warning(
            'KK fee entry %r already exists in Odoo for loan %s. Marking confirmed.',
            lms_ref, loan.loan_number,
        )
    except (OdooConnectionError, OdooPostingError) as exc:
        _logger.error(
            'Odoo error in handle_fee_collected for loan %s ref %s: %s',
            loan.loan_number, kk_ref, exc,
        )
        return None

    _mark_confirmed(kk_ref, move_id)
    return move_id


def handle_agent_collection(
    kk_ref: str,
    loan: Any,
    amount: float,
    agent_code: str,
    move_date: str | None = None,
) -> int | None:
    """
    Post an agent collection journal entry to Odoo.

    When a field agent collects cash on behalf of KK, it flows through:

      Dr 1107 KK Gateway Float
      Cr 4205 Agent Commission Income

    NOTE: Account 4205 (Agent Commission Income) must exist in Odoo's COA.
    If it does not, create it before running this handler.

    Idempotency key: 'AGNT-KK-{kk_ref}'

    Args:
        kk_ref:     Konse Konse transaction reference.
        loan:       LMS Loan instance.
        amount:     ZMW amount collected by the agent.
        agent_code: IntZam field agent identifier.
        move_date:  ISO date string; defaults to today.

    Returns:
        Odoo account.move id, or None on failure.
    """
    if _is_already_confirmed(kk_ref):
        _logger.info(
            'handle_agent_collection: ref=%s already CONFIRMED — skip.',
            kk_ref,
        )
        return None

    lms_ref  = f'AGNT-KK-{kk_ref}'
    entry_dt = _today(move_date)
    client   = get_odoo_client()
    move_id: int | None = None

    if not client.enabled:
        _logger.info('[Odoo disabled] Skipping KK agent collection sync for loan %s.', loan.loan_number)
        _mark_confirmed(kk_ref, None)
        return None

    try:
        client.authenticate()

        partner_id: int | None = loan.odoo_partner_id

        acct_1107  = client._account_id('1107')
        acct_4205  = client._account_id('4205')
        journal_id = client._journal_id('LFEE')

        move_vals = {
            'journal_id': journal_id,
            'date':       entry_dt,
            'ref':        lms_ref,
            'narration':  (
                f'KK Agent Collection | loan={loan.loan_number} '
                f'agent={agent_code} amount=ZMW{amount:.2f} kk_ref={kk_ref}'
            ),
            'line_ids': [
                # Dr 1107 KK Gateway Float
                (0, 0, {
                    'account_id': acct_1107,
                    'name':       f'KK Gateway Float — Agent {agent_code} {loan.loan_number}',
                    'debit':      float(amount),
                    'credit':     0.0,
                    'partner_id': partner_id,
                }),
                # Cr 4205 Agent Commission Income
                (0, 0, {
                    'account_id': acct_4205,
                    'name':       f'Agent Commission Income — {agent_code} {loan.loan_number}',
                    'debit':      0.0,
                    'credit':     float(amount),
                    'partner_id': partner_id,
                }),
            ],
        }

        move_id = client._create('account.move', move_vals)
        client._call('account.move', 'action_post', [[move_id]])

        _logger.info(
            'KK agent collection posted to Odoo: loan=%s agent=%s kk_ref=%s move_id=%s',
            loan.loan_number, agent_code, kk_ref, move_id,
        )

    except OdooDuplicateError:
        _logger.warning(
            'KK agent collection entry %r already exists in Odoo for loan %s.',
            lms_ref, loan.loan_number,
        )
    except (OdooConnectionError, OdooPostingError) as exc:
        _logger.error(
            'Odoo error in handle_agent_collection for loan %s ref %s: %s',
            loan.loan_number, kk_ref, exc,
        )
        return None

    _mark_confirmed(kk_ref, move_id)
    return move_id
