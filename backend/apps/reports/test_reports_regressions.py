from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.authentication.models import User
from apps.core.models import Client, InterestType, LoanProduct, QualifiedBase
from apps.loans.models import Loan, LoanStatus, Transaction, TransactionType


class ReportsRegressionTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='reports-admin',
            password='secret123',
            role='ADMIN',
            email='reports-admin@example.com',
        )
        self.client_profile = Client.objects.create(
            name='Reports Client',
            email='reports-client@example.com',
            phone='0973000001',
            nrc_number='REP-NRC-001',
            kyc_verified=True,
            monthly_income=10000,
        )
        self.product = LoanProduct.objects.create(
            name='Reports Product',
            description='Reports regression product',
            interest_type=InterestType.FLAT,
            interest_rate=25,
            nominal_interest_rate=18,
            credit_facilitation_fee=5,
            processing_fee=2,
            min_amount=500,
            max_amount=10000,
            min_term=1,
            max_term=12,
        )
        self.client.force_authenticate(user=self.admin)

    def _loan(self, **overrides):
        defaults = {
            'client': self.client_profile,
            'product': self.product,
            'amount': 1000,
            'purpose': 'Report regression',
            'term_months': 2,
            'interest_rate': 25,
            'total_repayable': 1250,
            'monthly_payment': 625,
            'repaid_amount': 250,
            'status': LoanStatus.ACTIVE,
            'days_overdue': 0,
            'disbursement_date': timezone.localdate() - timedelta(days=20),
            'maturity_date': timezone.localdate() + timedelta(days=40),
        }
        defaults.update(overrides)
        return Loan.objects.create(**defaults)

    def test_active_portfolio_uses_net_outstanding_and_expected_interest(self):
        self._loan(amount=1000, total_repayable=1250, repaid_amount=250)
        self._loan(amount=2000, total_repayable=2600, repaid_amount=600, status=LoanStatus.OVERDUE)

        response = self.client.get('/api/v1/reports/active-loan-portfolio/')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['summary']['total_disbursed'], 3000)
        self.assertEqual(response.data['summary']['total_expected_interest'], 850)
        self.assertEqual(response.data['summary']['total_outstanding'], 3000)
        self.assertEqual(response.data['by_product'][0]['total_outstanding'], 3000)

    def test_expected_collection_reports_interest_component(self):
        self._loan(
            amount=1000,
            total_repayable=1250,
            monthly_payment=625,
            repaid_amount=0,
            disbursement_date=timezone.localdate() - timedelta(days=20),
        )

        response = self.client.get('/api/v1/reports/expected-collection/?days=30')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['summary']['total_expected'], 625)
        self.assertEqual(response.data['summary']['total_expected_interest'], 125)
        self.assertEqual(response.data['data'][0]['expected_interest'], 125)

    def test_par_30_excludes_1_to_30_day_bucket(self):
        self._loan(total_repayable=1250, repaid_amount=250, days_overdue=20, status=LoanStatus.OVERDUE)
        self._loan(total_repayable=2400, repaid_amount=400, days_overdue=40, status=LoanStatus.OVERDUE)

        response = self.client.get('/api/v1/reports/aging-par-report/')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['par_amount'], 2000)
        self.assertEqual(response.data['par_30_ratio'], 66.7)

    def test_ifrs9_exposure_uses_net_outstanding(self):
        self._loan(total_repayable=1250, repaid_amount=250, days_overdue=0)
        self._loan(total_repayable=2400, repaid_amount=400, days_overdue=40, status=LoanStatus.OVERDUE)

        response = self.client.get('/api/v1/reports/ifrs9-expected-loss/')

        self.assertEqual(response.status_code, 200, response.data)
        stage_1 = next(row for row in response.data['stages'] if row['stage'] == 'Stage 1')
        stage_2 = next(row for row in response.data['stages'] if row['stage'] == 'Stage 2')
        self.assertEqual(stage_1['exposure'], 1000)
        self.assertEqual(stage_2['exposure'], 2000)

    def test_income_statement_reports_interest_component_not_full_repayment(self):
        loan = self._loan(amount=1000, total_repayable=1250, repaid_amount=250)
        Transaction.objects.create(
            loan=loan,
            transaction_type=TransactionType.REPAYMENT,
            amount=500,
            posted_by='reports-admin',
        )

        response = self.client.get('/api/v1/reports/income-statement/')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['income']['interest_income'], 100)
        self.assertEqual(response.data['income']['repayment_principal_component'], 400)

    def test_disbursement_register_uses_proper_client_name(self):
        self.client_profile.name = 'nazimvirani'
        self.client_profile.save(update_fields=['name'])
        QualifiedBase.objects.create(
            first_name='nazim',
            last_name='virani',
            phone_number=self.client_profile.phone,
            nrc_number=self.client_profile.nrc_number,
            amount_qualified_for=3000,
        )
        self._loan()

        response = self.client.get('/api/v1/reports/disbursement-register/')

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['data'][0]['client_name'], 'Nazim Virani')
