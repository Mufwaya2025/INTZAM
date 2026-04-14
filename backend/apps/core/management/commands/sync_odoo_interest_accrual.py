# -*- coding: utf-8 -*-
"""
sync_odoo_interest_accrual
==========================
Management command that posts month-end interest accrual journal entries
to Odoo for all ACTIVE and OVERDUE loans.

Section 8 mapping: Dr 1120 Interest Receivable / Cr 4101/4102/4103 Interest Income

The accrual amount is estimated as one month of EIR interest using the
loan's amortisation schedule instalment for the current period.

Run manually:
    python manage.py sync_odoo_interest_accrual
    python manage.py sync_odoo_interest_accrual --period 2026-03
    python manage.py sync_odoo_interest_accrual --dry-run

Cron (last day of each month, 23:00 CAT):
    0 23 28-31 * * /home/mufwaya/lms-venv/bin/python /mnt/f/LMS/backend/manage.py \
        sync_odoo_interest_accrual >> /var/log/lms/odoo_accrual_sync.log 2>&1
"""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.accounting.odoo_client import get_odoo_client, OdooConnectionError, OdooPostingError, OdooDuplicateError
from apps.loans.models import Loan, LoanStatus
from apps.loans.services import calculate_loan_terms


def _stage(days_overdue: int) -> str:
    if days_overdue > 90:
        return '3'
    if days_overdue >= 30:
        return '2'
    return '1'


def _monthly_interest(loan) -> float:
    """Estimate one month's interest from the amortisation schedule."""
    try:
        product = loan.product
        pricing_kwargs = {}
        if Decimal(str(loan.interest_rate)) == Decimal(str(product.interest_rate)):
            pricing_kwargs = {
                'nominal_interest_rate':   float(product.nominal_interest_rate),
                'credit_facilitation_fee': float(product.credit_facilitation_fee),
                'processing_fee':          float(product.processing_fee),
            }
        terms    = calculate_loan_terms(
            float(loan.amount), float(loan.interest_rate),
            loan.term_months, product.interest_type, **pricing_kwargs,
        )
        monthly  = float(loan.monthly_payment) or terms['monthly_payment']
        paid_cnt = int(float(loan.repaid_amount) / monthly) if monthly > 0 else 0
        idx      = min(paid_cnt, len(terms['schedule']) - 1)
        return round(terms['schedule'][idx]['interest'], 2)
    except Exception:
        return 0.0


class Command(BaseCommand):
    help = 'Post month-end interest accrual journal entries to Odoo'

    def add_arguments(self, parser):
        parser.add_argument('--period', type=str, metavar='YYYY-MM',
                            help='Accrual period (default: current month)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Log without making any Odoo calls')
        parser.add_argument('--loan', type=str, metavar='LOAN_NUMBER',
                            help='Process a single loan only')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        today   = date.today()
        period  = options['period'] or today.strftime('%Y-%m')
        client  = get_odoo_client()

        if not client.enabled and not dry_run:
            self.stderr.write(self.style.WARNING('ODOO_ENABLED=false — skipping.'))
            return

        qs = Loan.objects.filter(
            status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE]
        ).select_related('product')

        if options['loan']:
            qs = qs.filter(loan_number=options['loan'])

        total = qs.count()
        synced = skipped = errors = 0

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n  sync_odoo_interest_accrual  [{"DRY RUN" if dry_run else "LIVE"}]  period={period}\n'
        ))
        self.stdout.write(f'  Processing {total} loan(s)...\n')

        for loan in qs:
            accrual = _monthly_interest(loan)
            if accrual <= 0:
                skipped += 1
                continue

            stage = _stage(loan.days_overdue or 0)

            if dry_run:
                self.stdout.write(
                    f'  [DRY]  {loan.loan_number}  S{stage}  accrual={accrual:.2f}'
                )
                synced += 1
                continue

            try:
                move_id = client.post_interest_accrual(
                    loan=loan, accrual_amount=accrual,
                    period=period, ifrs9_stage=stage,
                    move_date=str(today),
                )
                self.stdout.write(self.style.SUCCESS(
                    f'  [OK]   {loan.loan_number}  S{stage}  accrual={accrual:.2f}  move_id={move_id}'
                ))
                synced += 1
            except OdooDuplicateError:
                self.stdout.write(f'  [SKIP] {loan.loan_number}  already accrued for {period}')
                skipped += 1
            except (OdooConnectionError, OdooPostingError) as exc:
                self.stderr.write(f'  [ERR]  {loan.loan_number}  {exc}')
                errors += 1

        self.stdout.write(
            f'\n  Done.  synced={synced}  skipped={skipped}  errors={errors}  total={total}\n'
        )
