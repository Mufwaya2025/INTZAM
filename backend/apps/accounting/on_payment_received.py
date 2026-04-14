# -*- coding: utf-8 -*-
"""
on_payment_received.py
======================
Event hook called by RepaymentView immediately after a borrower's payment
has been recorded and committed in the LMS database.

Responsibilities
----------------
1. Split the total payment into principal and interest components using the
   loan's amortisation schedule.
2. Determine the IFRS 9 stage from the loan's days_overdue.
3. Post a repayment journal entry in Odoo (Dr 1105 Bank / Cr 1111/1112/1113
   Loan Receivable + Cr 4101/4102/4103 Interest Income).
4. If a penalty amount is supplied, post a separate penalty entry.

Error policy
------------
All Odoo errors are caught and logged.  They do NOT propagate back to
RepaymentView — the LMS payment record is already committed and must not be
reversed because of a temporary Odoo issue.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from apps.accounting.odoo_client import (
    OdooConnectionError,
    OdooDuplicateError,
    OdooPostingError,
    get_odoo_client,
)
from apps.loans.services import calculate_loan_terms

_logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ifrs9_stage(loan) -> str:
    """
    Map days_overdue → IFRS 9 stage string ('1', '2', '3').

    BoZ classification:
        Stage 1: < 30 days overdue  (performing)
        Stage 2: 30-90 days overdue (under-performing)
        Stage 3: > 90 days overdue  (non-performing)
    """
    days = getattr(loan, 'days_overdue', 0) or 0
    if days > 90:
        return '3'
    if days >= 30:
        return '2'
    return '1'


def _split_payment(loan, total_amount: float) -> tuple[float, float]:
    """
    Split a payment into (principal, interest) portions.

    Strategy: build the amortisation schedule, identify which instalment
    we are currently on (based on repaid_amount before this payment), and
    use that instalment's principal/interest ratio.  Falls back to a
    proportional split from total loan economics if the schedule cannot
    be computed.

    Args:
        loan:         Loan instance (repaid_amount reflects state BEFORE
                      the current payment is added).
        total_amount: Total cash received.

    Returns:
        (principal, interest) rounded to 2 decimal places.
    """
    try:
        product = loan.product
        pricing_kwargs: dict = {}
        if Decimal(str(loan.interest_rate)) == Decimal(str(product.interest_rate)):
            pricing_kwargs = {
                'nominal_interest_rate'  : float(product.nominal_interest_rate),
                'credit_facilitation_fee': float(product.credit_facilitation_fee),
                'processing_fee'         : float(product.processing_fee),
            }
        terms = calculate_loan_terms(
            float(loan.amount),
            float(loan.interest_rate),
            loan.term_months,
            product.interest_type,
            **pricing_kwargs,
        )
        schedule = terms['schedule']
        monthly  = float(loan.monthly_payment) or terms['monthly_payment']

        # Which instalment are we settling?  Use repaid_amount BEFORE this payment.
        paid_count  = int(float(loan.repaid_amount) / monthly) if monthly > 0 else 0
        inst_index  = min(paid_count, len(schedule) - 1)
        entry       = schedule[inst_index]

        # Pro-rate the entry if this is a partial or over-payment.
        if monthly > 0 and entry['payment'] > 0:
            ratio = total_amount / entry['payment']
        else:
            ratio = 1.0

        principal = round(entry['principal'] * ratio, 2)
        interest  = round(total_amount - principal, 2)
        interest  = max(interest, 0.0)           # guard against floating-point drift
        principal = round(total_amount - interest, 2)
        return principal, interest

    except Exception as exc:
        _logger.warning(
            'Could not compute schedule split for loan %s (%s). '
            'Falling back to proportional split.',
            loan.loan_number, exc,
        )
        # Proportional fallback: derive ratio from total loan economics.
        total_repayable = float(loan.total_repayable)
        loan_principal  = float(loan.amount)
        if total_repayable > 0:
            interest_ratio = (total_repayable - loan_principal) / total_repayable
        else:
            interest_ratio = 0.0
        interest  = round(total_amount * interest_ratio, 2)
        principal = round(total_amount - interest, 2)
        return principal, interest


# ── Public hook ───────────────────────────────────────────────────────────────

def on_payment_received(
    loan,
    amount: float,
    payment_date: str | None = None,
    penalty_amount: float = 0.0,
    transaction_reference: str | None = None,
) -> int | None:
    """
    Post a repayment (and optional penalty) journal entry to Odoo when a
    borrower makes a payment.

    Called from RepaymentView immediately after the Transaction record is
    saved.  `loan.repaid_amount` has already been updated in the DB at this
    point — use the pre-payment balance if you need it (pass it explicitly).

    Args:
        loan:                  Loan instance (repaid_amount already updated).
        amount:                Total payment received (principal + interest).
        payment_date:          ISO date string; defaults to today.
        penalty_amount:        Additional penalty collected in this payment.
        transaction_reference: Optional LMS transaction reference for idempotency.

    Returns:
        int: Odoo account.move id for the repayment entry, or None on failure.
    """
    client = get_odoo_client()

    if not client.enabled:
        _logger.info(
            '[Odoo disabled] Skipping payment sync for loan %s.',
            loan.loan_number,
        )
        return None

    today        = str(date.today())
    move_date    = payment_date or today
    ifrs9_stage  = _ifrs9_stage(loan)

    # ── Split principal / interest ─────────────────────────────────────────────
    # loan.repaid_amount already includes this payment; subtract it to get
    # the pre-payment balance for schedule lookup.
    pre_payment_repaid = float(loan.repaid_amount) - amount
    # Temporarily patch for _split_payment calculation
    original_repaid   = loan.repaid_amount
    loan.repaid_amount = max(0.0, pre_payment_repaid)  # type: ignore[assignment]
    principal, interest = _split_payment(loan, amount)
    loan.repaid_amount  = original_repaid              # restore

    _logger.debug(
        'Payment split for loan %s: total=%.2f principal=%.2f interest=%.2f stage=%s',
        loan.loan_number, amount, principal, interest, ifrs9_stage,
    )

    # ── Resolve Odoo partner ───────────────────────────────────────────────────
    partner_id: int | None = loan.odoo_partner_id
    if partner_id is None:
        try:
            partner_id = client.sync_borrower(loan.client)
        except (OdooConnectionError, OdooPostingError) as exc:
            _logger.warning(
                'Could not sync borrower for loan %s: %s',
                loan.loan_number, exc,
            )

    # ── Build idempotency reference ────────────────────────────────────────────
    ref_suffix = transaction_reference or move_date
    repay_ref  = f'REPY-{loan.loan_number}-{ref_suffix}'

    # ── Post repayment entry ───────────────────────────────────────────────────
    move_id: int | None = None
    try:
        move_id = client.post_repayment(
            loan        = loan,
            principal   = principal,
            interest    = interest,
            move_date   = move_date,
            partner_id  = partner_id,
            reference   = repay_ref,
            ifrs9_stage = ifrs9_stage,
        )
        _logger.info(
            'Repayment posted to Odoo: loan=%s amount=%.2f move_id=%s stage=%s',
            loan.loan_number, amount, move_id, ifrs9_stage,
        )
    except OdooDuplicateError:
        _logger.warning(
            'Repayment entry %r already exists in Odoo for loan %s. Skipping.',
            repay_ref, loan.loan_number,
        )
    except (OdooConnectionError, OdooPostingError) as exc:
        _logger.error(
            'Odoo post_repayment failed for loan %s: %s',
            loan.loan_number, exc,
        )

    # ── Post penalty entry (if any) ────────────────────────────────────────────
    if penalty_amount and penalty_amount > 0:
        penalty_ref = f'PEN-{loan.loan_number}-{ref_suffix}'
        try:
            client.post_penalty(
                loan       = loan,
                amount     = penalty_amount,
                move_date  = move_date,
                partner_id = partner_id,
                reference  = penalty_ref,
            )
            _logger.info(
                'Penalty posted to Odoo: loan=%s amount=%.2f',
                loan.loan_number, penalty_amount,
            )
        except OdooDuplicateError:
            _logger.warning(
                'Penalty entry %r already exists in Odoo for loan %s. Skipping.',
                penalty_ref, loan.loan_number,
            )
        except (OdooConnectionError, OdooPostingError) as exc:
            _logger.error(
                'Odoo post_penalty failed for loan %s: %s',
                loan.loan_number, exc,
            )

    return move_id
