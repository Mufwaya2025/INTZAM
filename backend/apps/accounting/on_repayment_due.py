# -*- coding: utf-8 -*-
"""
on_repayment_due.py
===================
Event hook called by a scheduler (e.g. a Django management command run via
cron) when a loan instalment falls due.

Responsibilities
----------------
1. Calculate the instalment schedule from the loan product terms.
2. Identify the next unpaid instalment (by number and due date).
3. Create a customer invoice in Odoo for that instalment, splitting the
   payment into principal and interest lines.

Scheduler integration
---------------------
Wire this into a management command (apps/core/management/commands/) or a
Celery beat task.  Example management command snippet:

    from apps.loans.models import Loan, LoanStatus
    from apps.accounting.on_repayment_due import on_repayment_due

    for loan in Loan.objects.filter(status__in=['ACTIVE', 'OVERDUE']):
        on_repayment_due(loan)

Error policy
------------
Odoo errors are caught and logged.  They never crash the scheduler loop.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from apps.accounting.odoo_client import (
    OdooConnectionError,
    OdooPostingError,
    get_odoo_client,
)
from apps.loans.services import calculate_loan_terms

_logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_schedule(loan) -> list[dict]:
    """
    Return the amortisation schedule for the loan.
    Each entry: {'month': int, 'payment': float, 'principal': float,
                 'interest': float, 'balance': float}
    """
    product = loan.product
    pricing_kwargs: dict = {}
    if Decimal(str(loan.interest_rate)) == Decimal(str(product.interest_rate)):
        pricing_kwargs = {
            'nominal_interest_rate': float(product.nominal_interest_rate),
            'credit_facilitation_fee': float(product.credit_facilitation_fee),
            'processing_fee': float(product.processing_fee),
        }
    terms = calculate_loan_terms(
        float(loan.amount),
        float(loan.interest_rate),
        loan.term_months,
        product.interest_type,
        **pricing_kwargs,
    )
    return terms['schedule']


def _instalment_number(loan) -> int:
    """
    Estimate the 1-based instalment number of the *next* payment due.

    Uses repaid_amount / monthly_payment to determine how many full
    instalments have been received, then returns the next one.
    """
    monthly = float(loan.monthly_payment)
    if monthly <= 0:
        return 1
    paid_count = int(float(loan.repaid_amount) / monthly)
    return min(paid_count + 1, loan.term_months)


def _due_date(loan, instalment_number: int) -> date:
    """
    Compute the calendar due date for a given instalment number.
    Assumes monthly payments from the disbursement date.
    """
    base = loan.disbursement_date or date.today()
    return base + timedelta(days=30 * instalment_number)


# ── Public hook ───────────────────────────────────────────────────────────────

def on_repayment_due(loan) -> int | None:
    """
    Create an Odoo repayment invoice for the next instalment due on `loan`.

    Called by the scheduler for every ACTIVE / OVERDUE loan when its
    instalment date arrives.

    Args:
        loan: apps.loans.models.Loan instance.

    Returns:
        int: Odoo account.move (invoice) id, or None on failure / disabled.
    """
    client = get_odoo_client()

    if not client.enabled:
        _logger.info(
            '[Odoo disabled] Skipping repayment invoice for loan %s.',
            loan.loan_number,
        )
        return None

    # ── Resolve instalment details ─────────────────────────────────────────────
    try:
        schedule       = _get_schedule(loan)
        inst_no        = _instalment_number(loan)
        inst_due_date  = _due_date(loan, inst_no)

        if inst_no > len(schedule):
            _logger.info(
                'Loan %s is fully scheduled (%d/%d instalments). Nothing to invoice.',
                loan.loan_number, inst_no - 1, loan.term_months,
            )
            return None

        entry     = schedule[inst_no - 1]   # 0-indexed list
        principal = round(entry['principal'], 2)
        interest  = round(entry['interest'],  2)

        _logger.info(
            'Instalment %d/%d for loan %s: principal=%.2f interest=%.2f due=%s',
            inst_no, loan.term_months, loan.loan_number,
            principal, interest, inst_due_date,
        )
    except Exception as calc_exc:
        _logger.error(
            'Could not compute instalment for loan %s: %s',
            loan.loan_number, calc_exc,
        )
        return None

    # ── Resolve Odoo partner ───────────────────────────────────────────────────
    partner_id: int | None = loan.odoo_partner_id
    if partner_id is None:
        try:
            partner_id = client.sync_borrower(loan.client)
        except (OdooConnectionError, OdooPostingError) as exc:
            _logger.warning(
                'Could not sync borrower for loan %s: %s. Invoice will have no partner.',
                loan.loan_number, exc,
            )

    # ── Create invoice in Odoo ─────────────────────────────────────────────────
    invoice_ref = f'INV-{loan.loan_number}-{inst_no:02d}-{inst_due_date}'
    try:
        invoice_id = client.create_repayment_invoice(
            loan       = loan,
            principal  = principal,
            interest   = interest,
            due_date   = str(inst_due_date),
            partner_id = partner_id,
            invoice_ref = invoice_ref,
        )
        _logger.info(
            'Repayment invoice created: loan=%s inst=%d invoice_id=%s',
            loan.loan_number, inst_no, invoice_id,
        )
        return invoice_id

    except (OdooConnectionError, OdooPostingError) as exc:
        _logger.error(
            'Odoo create_repayment_invoice failed for loan %s instalment %d: %s',
            loan.loan_number, inst_no, exc,
        )
        return None
