from django.test import override_settings
from rest_framework.test import APITestCase

from apps.authentication.models import User
from apps.core.models import Client, InterestType, LoanProduct, QualifiedBase
from apps.loans.models import CGRateTransaction, CGRateTransactionStatus, CGRateTransactionType, Loan, LoanStatus


class CGRateIntegrationTests(APITestCase):
    def setUp(self):
        self.client_user = User.objects.create_user(
            username='cgrate-client',
            password='secret123',
            role='CLIENT',
            email='cgrate.client@example.com',
            phone='0973000001',
        )
        self.accountant = User.objects.create_user(
            username='cgrate-accountant',
            password='secret123',
            role='ACCOUNTANT',
            email='cgrate.accountant@example.com',
        )
        self.client_profile = Client.objects.create(
            user=self.client_user,
            name='CGRate Client',
            email='cgrate.client@example.com',
            phone='0973000001',
            nrc_number='CGRATE-NRC-001',
            kyc_verified=True,
        )
        QualifiedBase.objects.create(
            first_name='CGRate',
            last_name='Client',
            phone_number=self.client_profile.phone,
            nrc_number=self.client_profile.nrc_number,
            amount_qualified_for=5000,
        )
        self.product = LoanProduct.objects.create(
            name='CGRate Product',
            description='CGRate integration regression product',
            interest_type=InterestType.FLAT,
            interest_rate=25,
            nominal_interest_rate=18,
            credit_facilitation_fee=5,
            processing_fee=2,
            min_amount=500,
            max_amount=5000,
            min_term=1,
            max_term=12,
        )
        self.loan = Loan.objects.create(
            client=self.client_profile,
            product=self.product,
            amount=1000,
            purpose='CGRate regression',
            term_months=1,
            interest_rate=25,
            total_repayable=1250,
            monthly_payment=1250,
            status=LoanStatus.ACTIVE,
        )

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_cgrate_collection_is_blocked_before_disbursement(self):
        self.loan.status = LoanStatus.APPROVED
        self.loan.save(update_fields=['status'])

        self._auth(self.client_user)
        response = self.client.post(
            f'/api/v1/loans/{self.loan.id}/cgrate-collect/',
            {'amount': '100'},
            format='json',
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn('active or overdue', response.data['error'])
        self.assertFalse(CGRateTransaction.objects.exists())

    @override_settings(CGRATE_ENABLED=False)
    def test_disabled_cgrate_collection_records_pending_without_repaying_loan(self):
        self._auth(self.client_user)
        response = self.client.post(
            f'/api/v1/loans/{self.loan.id}/cgrate-collect/',
            {'amount': '100', 'notes': 'Mobile money payment'},
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.data)
        txn = CGRateTransaction.objects.get()
        self.assertEqual(txn.transaction_type, CGRateTransactionType.COLLECTION)
        self.assertEqual(txn.status, CGRateTransactionStatus.PENDING)
        self.loan.refresh_from_db()
        self.assertEqual(self.loan.repaid_amount, 0)
        self.assertFalse(self.loan.transactions.exists())

    def test_client_cannot_view_cgrate_transactions_list(self):
        CGRateTransaction.objects.create(
            loan=self.loan,
            transaction_type=CGRateTransactionType.COLLECTION,
            name=self.client_profile.name,
            email=self.client_profile.email,
            phone_number='260973000001',
            amount=100,
            reference='PAY-CGRATE-001',
            service='MTN',
        )

        self._auth(self.client_user)
        response = self.client.get('/api/v1/cgrate/transactions/')

        self.assertEqual(response.status_code, 403, response.data)

    @override_settings(CGRATE_ENABLED=False)
    def test_duplicate_cgrate_disbursement_is_blocked(self):
        self._auth(self.accountant)
        first = self.client.post(f'/api/v1/loans/{self.loan.id}/cgrate-disburse/', {}, format='json')
        second = self.client.post(f'/api/v1/loans/{self.loan.id}/cgrate-disburse/', {}, format='json')

        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 400, second.data)
        self.assertEqual(
            CGRateTransaction.objects.filter(transaction_type=CGRateTransactionType.DISBURSEMENT).count(),
            1,
        )
