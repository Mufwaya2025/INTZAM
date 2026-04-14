# -*- coding: utf-8 -*-
"""
sync_odoo_repayment_invoices
============================
Management command that creates Odoo repayment invoices for every
ACTIVE / OVERDUE loan whose next instalment is due today or earlier.

Run manually:
    python manage.py sync_odoo_repayment_invoices

Run with dry-run (no Odoo writes):
    python manage.py sync_odoo_repayment_invoices --dry-run

Cron (daily 08:00 CAT):
    0 8 * * * /home/mufwaya/lms-venv/bin/python /mnt/f/LMS/backend/manage.py \
        sync_odoo_repayment_invoices >> /var/log/lms/odoo_repayment_sync.log 2>&1
"""

from datetime import date

from django.core.management.base import BaseCommand

from apps.accounting.on_repayment_due import on_repayment_due, _due_date, _instalment_number
from apps.accounting.odoo_client import get_odoo_client
from apps.loans.models import Loan, LoanStatus


class Command(BaseCommand):
    help = 'Create Odoo repayment invoices for all loans with instalments due today or earlier'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Log what would be posted without making any Odoo calls',
        )
        parser.add_argument(
            '--loan',
            type=str,
            metavar='LOAN_NUMBER',
            help='Process a single loan number only (for testing)',
        )

    def handle(self, *args, **options):
        dry_run  = options['dry_run']
        today    = date.today()
        client   = get_odoo_client()

        if not client.enabled and not dry_run:
            self.stderr.write(self.style.WARNING(
                'ODOO_ENABLED=false — no invoices will be created. '
                'Set ODOO_ENABLED=true in .env to enable.'
            ))
            return

        # ── Select loans ──────────────────────────────────────────────────────
        qs = Loan.objects.filter(
            status__in=[LoanStatus.ACTIVE, LoanStatus.OVERDUE]
        ).select_related('client', 'product')

        if options['loan']:
            qs = qs.filter(loan_number=options['loan'])

        total   = qs.count()
        skipped = 0
        synced  = 0
        errors  = 0

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f'\n  sync_odoo_repayment_invoices  '
                f'[{"DRY RUN" if dry_run else "LIVE"}]  {today}'
            )
        )
        self.stdout.write(f'  Processing {total} loan(s)...\n')

        for loan in qs:
            # Only invoice loans with a known disbursement date
            if not loan.disbursement_date:
                skipped += 1
                continue

            # Only create invoice if the next instalment is due today or overdue
            try:
                inst_no  = _instalment_number(loan)
                due      = _due_date(loan, inst_no)
            except Exception as exc:
                self.stderr.write(
                    f'  [ERROR] {loan.loan_number}: could not compute due date — {exc}'
                )
                errors += 1
                continue

            if due > today:
                skipped += 1
                self.stdout.write(
                    f'  [SKIP]  {loan.loan_number}  inst {inst_no}  due {due}  (not yet due)'
                )
                continue

            if dry_run:
                self.stdout.write(
                    f'  [DRY]   {loan.loan_number}  inst {inst_no}  due {due}  '
                    f'— would call on_repayment_due()'
                )
                synced += 1
                continue

            # ── Live call ─────────────────────────────────────────────────────
            invoice_id = on_repayment_due(loan)
            if invoice_id:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  [OK]    {loan.loan_number}  inst {inst_no}  due {due}  '
                        f'invoice_id={invoice_id}'
                    )
                )
                synced += 1
            else:
                self.stderr.write(
                    f'  [ERROR] {loan.loan_number}  inst {inst_no}  due {due}  '
                    f'— on_repayment_due() returned None (check logs)'
                )
                errors += 1

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write(
            f'\n  Done.  synced={synced}  skipped={skipped}  errors={errors}  '
            f'total={total}\n'
        )

        if errors:
            self.stderr.write(
                self.style.WARNING('  Some loans had errors — check Django logs for details.')
            )
