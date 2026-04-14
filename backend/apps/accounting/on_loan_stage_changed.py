# -*- coding: utf-8 -*-
"""
on_loan_stage_changed.py
========================
Event hook called by the daily overdue-update management command when a
loan's IFRS 9 stage changes (days_overdue crosses the 30 or 90 day threshold).

Section 8 mapping
-----------------
S1 → S2:  Dr 5102 Provision Exp S2 / Cr 1202 Provision S2
S2 → S3:  Dr 5103 Provision Exp S3 / Cr 1203 Provision S3
S3 → S2:  Dr 1203 Provision S3    / Cr 5103 Provision Exp S3  (cure)
S2 → S1:  Dr 1202 Provision S2    / Cr 5102 Provision Exp S2  (cure)

ECL amount
----------
A simplified ECL estimate is used here:
  Stage 1:  1%  of outstanding principal
  Stage 2:  15% of outstanding principal
  Stage 3:  50% of outstanding principal

These rates should be replaced with the institution's actual ECL model
when full IFRS 9 ECL calculations are implemented.

Error policy
------------
Odoo errors are caught and logged. They never crash the caller.
"""

from __future__ import annotations

import logging

from apps.accounting.odoo_client import (
    OdooConnectionError,
    OdooDuplicateError,
    OdooPostingError,
    get_odoo_client,
)

_logger = logging.getLogger(__name__)

# Simplified ECL rates by stage (replace with actuarial model later)
_ECL_RATES = {'1': 0.01, '2': 0.15, '3': 0.50}


def _ifrs9_stage(days_overdue: int) -> str:
    """Map days_overdue to IFRS 9 stage string."""
    if days_overdue > 90:
        return '3'
    if days_overdue >= 30:
        return '2'
    return '1'


def _ecl_amount(loan, to_stage: str) -> float:
    """Estimate incremental ECL for the transition to `to_stage`."""
    outstanding = float(loan.total_repayable) - float(loan.repaid_amount)
    return round(outstanding * _ECL_RATES.get(to_stage, 0.01), 2)


def on_stage_changed(
    loan,
    from_stage: str,
    to_stage: str,
    ecl_amount: float | None = None,
    move_date: str | None = None,
) -> int | None:
    """
    Post an IFRS 9 stage transfer provision entry to Odoo.

    Called from update_loan_statuses management command when a loan's
    days_overdue crosses a stage boundary.

    Args:
        loan:       Loan instance.
        from_stage: Previous IFRS 9 stage ('1', '2', or '3').
        to_stage:   New IFRS 9 stage ('1', '2', or '3').
        ecl_amount: ECL provision amount. If None, estimated from outstanding balance.
        move_date:  ISO date string; defaults to today.

    Returns:
        int: Odoo account.move id, or None on failure / disabled.
    """
    client = get_odoo_client()

    if not client.enabled:
        _logger.info('[Odoo disabled] Skipping stage transfer for loan %s.', loan.loan_number)
        return None

    if from_stage == to_stage:
        return None

    if ecl_amount is None:
        ecl_amount = _ecl_amount(loan, to_stage)

    if ecl_amount <= 0:
        _logger.info('ECL amount is zero for stage transfer on loan %s — skipping.', loan.loan_number)
        return None

    try:
        move_id = client.post_stage_transfer(
            loan=loan,
            from_stage=from_stage,
            to_stage=to_stage,
            ecl_amount=ecl_amount,
            move_date=move_date,
        )
        _logger.info(
            'Stage transfer posted: loan=%s S%s→S%s ecl=%.2f move_id=%s',
            loan.loan_number, from_stage, to_stage, ecl_amount, move_id,
        )
        return move_id
    except OdooDuplicateError:
        _logger.warning(
            'Stage transfer already posted for loan %s S%s→S%s. Skipping.',
            loan.loan_number, from_stage, to_stage,
        )
        return None
    except (OdooConnectionError, OdooPostingError) as exc:
        _logger.error(
            'Odoo post_stage_transfer failed for loan %s S%s→S%s: %s',
            loan.loan_number, from_stage, to_stage, exc,
        )
        return None
