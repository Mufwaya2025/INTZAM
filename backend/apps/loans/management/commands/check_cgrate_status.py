from django.core.management.base import BaseCommand

from apps.loans.cgrate_service import CGRatePaymentService
from apps.loans.models import CGRateTransaction, CGRateTransactionStatus


class Command(BaseCommand):
    help = 'Check CGRate status for pending/processing transactions.'

    def add_arguments(self, parser):
        parser.add_argument('--all', action='store_true', help='Check all CGRate transactions.')
        parser.add_argument('--limit', type=int, default=100, help='Maximum transactions to check.')

    def handle(self, *args, **options):
        qs = CGRateTransaction.objects.all()
        if not options['all']:
            qs = qs.filter(status__in=[CGRateTransactionStatus.PENDING, CGRateTransactionStatus.PROCESSING])
        qs = qs.order_by('created_at')[:options['limit']]

        service = CGRatePaymentService()
        completed = failed = unchanged = errors = 0
        total = len(qs)
        self.stdout.write(f'Checking {total} CGRate transaction(s).')

        for txn in qs:
            before = txn.status
            try:
                txn = service.refresh_transaction_status(txn)
            except Exception as exc:
                errors += 1
                self.stdout.write(self.style.ERROR(f'{txn.reference}: ERROR {exc}'))
                continue

            if txn.status == CGRateTransactionStatus.COMPLETED and before != txn.status:
                completed += 1
                self.stdout.write(self.style.SUCCESS(f'{txn.reference}: Completed ({txn.external_ref})'))
            elif txn.status == CGRateTransactionStatus.FAILED and before != txn.status:
                failed += 1
                self.stdout.write(self.style.WARNING(f'{txn.reference}: Failed'))
            else:
                unchanged += 1
                self.stdout.write(f'{txn.reference}: {txn.status}')

        self.stdout.write(self.style.SUCCESS(
            f'Done: total={total}, completed={completed}, failed={failed}, unchanged={unchanged}, errors={errors}'
        ))
