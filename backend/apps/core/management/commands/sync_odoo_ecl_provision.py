# -*- coding: utf-8 -*-
"""
sync_odoo_ecl_provision
=======================
Management command that posts monthly IFRS 9 ECL provision journal entries
to Odoo for all ACTIVE, OVERDUE, and WRITTEN_OFF loans.

Section 8 mapping: Dr 5101/5102/5103 Provision Exp / Cr 1201/1202/1203 Provision

Run manually:
    python manage.py sync_odoo_ecl_provision
    python manage.py sync_odoo_ecl_provision --period 2026-03
    python manage.py sync_odoo_ecl_provision --dry-run

Cron (1st of each month, 07:00 CAT):
    0 7 1 * * /home/mufwaya/lms-venv/bin/python /mnt/f/LMS/backend/manage.py \
        sync_odoo_ecl_provision >> /var/log/lms/odoo_ecl_sync.log 2>&1
"""

from datetime import date

from django.core.management.base import BaseCommand

from apps.accounting.odoo_client import get_odoo_client, OdooConnectionError, OdooPostingError, OdooDuplicateError
from apps.loans.models import Loan, LoanStatus

# Simplified ECL rates — replace with actuarial model when available
_ECL_RATES = {'1': 0.01, '2': 0.15, '3': 0.50}


def _stage(days_overdue: int) -> str:
    if days_overdue > 90:
        return '3'
    if days_overdue >= 30:
        return '2'
    return '1'


class Command(BaseCommand):
    help = 'Post monthly IFRS 9 ECL provision entries to Odoo for all active/overdue loans'

    def add_arguments(self, parser):
        parser.add_argument(
            '--period', type=str, metavar='YYYY-MM',
            help='Accrual period (default: current month)',
        )
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
            status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE, LoanStatus.WRITTEN_OFF]
        ).select_related('client', 'product')

        if options['loan']:
            qs = qs.filter(loan_number=options['loan'])

        total = qs.count()
        synced = skipped = errors = 0

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n  sync_odoo_ecl_provision  [{"DRY RUN" if dry_run else "LIVE"}]  period={period}\n'
        ))
        self.stdout.write(f'  Processing {total} loan(s)...\n')

        for loan in qs:
            outstanding = float(loan.total_repayable) - float(loan.repaid_amount)
            if outstanding <= 0:
                skipped += 1
                continue

            stage      = _stage(loan.days_overdue or 0)
            ecl_amount = round(outstanding * _ECL_RATES[stage], 2)

            if dry_run:
                self.stdout.write(
                    f'  [DRY]  {loan.loan_number}  S{stage}  outstanding={outstanding:.2f}'
                    f'  ecl={ecl_amount:.2f}'
                )
                synced += 1
                continue

            try:
                move_id = client.post_ecl_provision(
                    loan_id=loan.loan_number,
                    ecl_amount=ecl_amount,
                    stage=stage,
                    move_date=str(today),
                    reference=f'ECL-{loan.loan_number}-S{stage}-{period}',
                )
                self.stdout.write(self.style.SUCCESS(
                    f'  [OK]   {loan.loan_number}  S{stage}  ecl={ecl_amount:.2f}  move_id={move_id}'
                ))
                synced += 1
            except OdooDuplicateError:
                self.stdout.write(f'  [SKIP] {loan.loan_number}  already posted for {period}')
                skipped += 1
            except (OdooConnectionError, OdooPostingError) as exc:
                self.stderr.write(f'  [ERR]  {loan.loan_number}  {exc}')
                errors += 1

        self.stdout.write(
            f'\n  Done.  synced={synced}  skipped={skipped}  errors={errors}  total={total}\n'
        )
