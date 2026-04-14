# -*- coding: utf-8 -*-
"""
momo_reconcile.py  (Prompt 22)
================================
Matches incoming mobile money payment notifications to open Odoo invoices,
registers payments, and handles partial payments.

Called from MoMoWebhookView (POST /api/accounting/momo-webhook/).

Flow
----
1. Validate the incoming payload (amount, reference, MNO).
2. Extract loan reference from the MoMo narration / reference field.
3. Find the matching open Odoo invoice (account.move, move_type='out_invoice').
4. Register the payment via Odoo account.payment XML-RPC.
5. Post MoMo Levy (Act 25/2024) if applicable.
6. Log the event to lms.loan.event for idempotency.
7. Return a result dict indicating success, partial, duplicate, or not-found.

Payload format (from MTN / Airtel webhook)
------------------------------------------
{
  "mno":           "MTN" | "AIRTEL" | "ZAMTEL",
  "reference":     "P250316001234",          # MNO transaction reference
  "amount":        "500.00",                 # ZMW amount received
  "phone":         "0971234567",
  "narration":     "LMS-LOAN-2024-001",      # loan number or LMS reference
  "timestamp":     "2026-03-16T10:30:00Z"
}
"""

from __future__ import annotations

import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from apps.accounting.odoo_client import (
    OdooConnectionError,
    OdooDuplicateError,
    OdooPostingError,
    get_odoo_client,
)

_logger = logging.getLogger(__name__)

# MoMo Levy rate — Act No. 25 of 2024 (0.2% capped at ZMW 2.00 per transaction)
_MOMO_LEVY_RATE = 0.002
_MOMO_LEVY_CAP  = 2.00

# Mapping from MNO name to float account code
_FLOAT_ACCOUNTS = {
    'MTN':    '1102',
    'AIRTEL': '1103',
    'ZAMTEL': '1104',
}


def _extract_loan_ref(text: str) -> str | None:
    """
    Extract a loan reference from a MoMo narration string.

    Looks for patterns like:
      'LMS-LOAN-2024-001'  →  'LOAN-2024-001'
      'LOAN2024001'        →  'LOAN2024001'
      'REF: LOAN-2024-001' →  'LOAN-2024-001'
    """
    if not text:
        return None
    # Explicit LMS- prefix
    m = re.search(r'LMS[-\s]?(LOAN[-\w]+)', text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # Bare LOAN- pattern
    m = re.search(r'\b(LOAN[-\w]+)\b', text, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    return None


def _momo_levy(amount: float) -> float:
    """Calculate MoMo levy: 0.2% of amount, capped at ZMW 2.00."""
    return round(min(amount * _MOMO_LEVY_RATE, _MOMO_LEVY_CAP), 2)


def reconcile_momo_payment(payload: dict) -> dict:
    """
    Match a MoMo payment to an open Odoo invoice and register the payment.

    Args:
        payload: Dict with keys: mno, reference, amount, phone, narration, timestamp

    Returns:
        dict with keys:
          status:       'paid' | 'partial' | 'duplicate' | 'not_found' | 'error'
          invoice_id:   Odoo account.move id (int) or None
          payment_id:   Odoo account.payment id (int) or None
          amount_paid:  float amount registered
          outstanding:  float remaining on invoice after payment
          loan_ref:     loan reference extracted from narration
          momo_ref:     MNO transaction reference
          message:      human-readable result
    """
    client = get_odoo_client()

    mno       = (payload.get('mno') or 'MTN').upper()
    momo_ref  = payload.get('reference', '')
    narration = payload.get('narration', '')
    phone     = payload.get('phone', '')

    try:
        amount = round(float(Decimal(str(payload.get('amount', 0)))), 2)
    except (InvalidOperation, TypeError):
        return _result('error', message=f'Invalid amount: {payload.get("amount")}',
                       momo_ref=momo_ref)

    if amount <= 0:
        return _result('error', message='Amount must be positive', momo_ref=momo_ref)

    # ── 1. Extract loan reference ──────────────────────────────────────────────
    loan_ref = _extract_loan_ref(narration) or _extract_loan_ref(momo_ref)
    if not loan_ref:
        _logger.warning('MoMo payment %s: cannot extract loan ref from "%s"', momo_ref, narration)
        return _result('not_found',
                       message=f'Cannot extract loan reference from narration: "{narration}"',
                       momo_ref=momo_ref)

    # ── 2. Idempotency — check if already processed ───────────────────────────
    if client.enabled:
        try:
            already = client._search(
                'lms.loan.event',
                [['konse_reference', '=', momo_ref]],
                limit=1,
            )
            if already:
                _logger.info('MoMo ref %s already processed (event id=%s). Skipping.', momo_ref, already[0])
                return _result('duplicate',
                               message=f'MoMo reference {momo_ref} already processed.',
                               momo_ref=momo_ref, loan_ref=loan_ref)
        except (OdooConnectionError, OdooPostingError) as exc:
            _logger.warning('Could not check lms.loan.event for idempotency: %s', exc)

    # ── 3. Find matching open invoice ─────────────────────────────────────────
    invoice_id = None
    invoice    = None

    if client.enabled:
        try:
            # Search by invoice ref field (set to 'INV-<loan_number>-<inst>-<date>' by on_repayment_due)
            invoices = client._search_read(
                'account.move',
                [
                    ['ref', 'ilike', loan_ref],
                    ['move_type', '=', 'out_invoice'],
                    ['payment_state', 'in', ['not_paid', 'partial']],
                    ['state', '=', 'posted'],
                ],
                ['id', 'ref', 'amount_total', 'amount_residual', 'partner_id',
                 'invoice_date_due'],
                limit=1,
                order='invoice_date_due asc',
            )

            if not invoices:
                # Fallback: search by partner phone
                if phone:
                    partners = client._search_read(
                        'res.partner',
                        [['phone', '=', phone]],
                        ['id'],
                        limit=1,
                    )
                    if partners:
                        partner_id = partners[0]['id']
                        invoices = client._search_read(
                            'account.move',
                            [
                                ['partner_id', '=', partner_id],
                                ['move_type', '=', 'out_invoice'],
                                ['payment_state', 'in', ['not_paid', 'partial']],
                                ['state', '=', 'posted'],
                            ],
                            ['id', 'ref', 'amount_total', 'amount_residual',
                             'partner_id', 'invoice_date_due'],
                            limit=1,
                            order='invoice_date_due asc',
                        )

            if not invoices:
                _logger.warning('No open invoice found for loan_ref=%s phone=%s', loan_ref, phone)
                return _result('not_found',
                               message=f'No open invoice found for loan ref {loan_ref!r}.',
                               momo_ref=momo_ref, loan_ref=loan_ref)

            invoice    = invoices[0]
            invoice_id = invoice['id']

        except (OdooConnectionError, OdooPostingError) as exc:
            _logger.error('Odoo invoice lookup failed: %s', exc)
            return _result('error', message=f'Odoo error during invoice lookup: {exc}',
                           momo_ref=momo_ref, loan_ref=loan_ref)

    # ── 4. Register the payment ───────────────────────────────────────────────
    payment_id  = None
    outstanding = float(invoice['amount_residual']) if invoice else 0.0
    amount_to_pay = min(amount, outstanding)

    if client.enabled and invoice_id:
        try:
            journal_id = client._journal_id('LRPY')

            payment_vals = {
                'payment_type':        'inbound',
                'partner_type':        'customer',
                'partner_id':          invoice['partner_id'][0] if isinstance(invoice['partner_id'], list) else invoice['partner_id'],
                'amount':              amount_to_pay,
                'date':                str(date.today()),
                'journal_id':          journal_id,
                'ref':                 momo_ref,
                'memo':                f'MoMo {mno} | {narration} | LMS {loan_ref}',
            }
            payment_id = client._create('account.payment', payment_vals)
            # Confirm (post) the payment
            client._call('account.payment', 'action_post', [[payment_id]])

            # Reconcile payment with the invoice
            payment_lines = client._search_read(
                'account.move.line',
                [['payment_id', '=', payment_id],
                 ['account_id.account_type', '=', 'asset_receivable']],
                ['id'],
            )
            invoice_lines = client._search_read(
                'account.move.line',
                [['move_id', '=', invoice_id],
                 ['account_id.account_type', '=', 'asset_receivable'],
                 ['reconciled', '=', False]],
                ['id'],
            )
            if payment_lines and invoice_lines:
                all_line_ids = [l['id'] for l in payment_lines + invoice_lines]
                client._call('account.move.line', 'reconcile', [all_line_ids])

            _logger.info(
                'MoMo payment registered: ref=%s loan=%s amount=%.2f invoice_id=%s payment_id=%s',
                momo_ref, loan_ref, amount_to_pay, invoice_id, payment_id,
            )

        except (OdooConnectionError, OdooPostingError) as exc:
            _logger.error('Odoo payment registration failed for %s: %s', momo_ref, exc)
            return _result('error', message=f'Odoo payment error: {exc}',
                           invoice_id=invoice_id, momo_ref=momo_ref, loan_ref=loan_ref)

    # ── 5. Post MoMo levy ─────────────────────────────────────────────────────
    levy = _momo_levy(amount)
    if client.enabled and levy > 0:
        float_code = _FLOAT_ACCOUNTS.get(mno, '1102')
        try:
            # Needs a loan object stub for the client method — use a simple namespace
            class _LoanStub:
                loan_number = loan_ref
            client.post_momo_levy(
                loan=_LoanStub(),
                levy_amount=levy,
                float_account=float_code,
                reference=f'LEVY-{momo_ref}',
            )
            _logger.info('MoMo levy posted: ref=%s levy=%.2f float=%s', momo_ref, levy, float_code)
        except (OdooDuplicateError, OdooConnectionError, OdooPostingError) as exc:
            _logger.warning('MoMo levy post failed for %s: %s', momo_ref, exc)

    # ── 6. Log to lms.loan.event ──────────────────────────────────────────────
    if client.enabled:
        try:
            client._create('lms.loan.event', {
                'lms_reference':    f'MOMO-{momo_ref}',
                'konse_reference':  momo_ref,
                'event_type':       'repayment_principal',
                'amount':           amount_to_pay,
                'event_date':       str(date.today()),
                'notes':            f'{mno} | {narration} | loan={loan_ref}',
            })
        except Exception as exc:
            _logger.warning('Could not log lms.loan.event for %s: %s', momo_ref, exc)

    # ── 7. Result ─────────────────────────────────────────────────────────────
    remaining = round(outstanding - amount_to_pay, 2)
    pay_status = 'paid' if remaining <= 0 else 'partial'
    return _result(
        pay_status,
        invoice_id=invoice_id,
        payment_id=payment_id,
        amount_paid=amount_to_pay,
        outstanding=remaining,
        loan_ref=loan_ref,
        momo_ref=momo_ref,
        message=(
            f'{mno} payment of ZMW {amount_to_pay:.2f} registered against invoice {invoice_id}. '
            f'Remaining: ZMW {remaining:.2f}.'
        ),
    )


def _result(
    status: str, *,
    invoice_id=None, payment_id=None,
    amount_paid=0.0, outstanding=0.0,
    loan_ref=None, momo_ref=None,
    message='',
) -> dict:
    return {
        'status':      status,
        'invoice_id':  invoice_id,
        'payment_id':  payment_id,
        'amount_paid': amount_paid,
        'outstanding': outstanding,
        'loan_ref':    loan_ref,
        'momo_ref':    momo_ref,
        'message':     message,
    }
