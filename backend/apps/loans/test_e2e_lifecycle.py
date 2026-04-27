from rest_framework.test import APITestCase

from apps.authentication.models import User
from apps.core.models import (
    Client,
    FieldType,
    InterestType,
    KYCField,
    KYCSection,
    KYCSubmission,
    LoanProduct,
)
from apps.loans.models import Loan, LoanStatus, TransactionType


class ClientLoanLifecycleE2ETests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='admin-e2e',
            password='secret123',
            role='ADMIN',
            email='admin-e2e@example.com',
        )
        self.underwriter = User.objects.create_user(
            username='underwriter-e2e',
            password='secret123',
            role='UNDERWRITER',
            email='underwriter-e2e@example.com',
        )
        self.accountant = User.objects.create_user(
            username='accountant-e2e',
            password='secret123',
            role='ACCOUNTANT',
            email='accountant-e2e@example.com',
        )

        section = KYCSection.objects.create(name='Identity', order=1, is_active=True)
        KYCField.objects.create(
            section=section,
            name='nrc_front',
            label='NRC Front',
            field_type=FieldType.TEXT,
            required=True,
            order=1,
        )

        self.product = LoanProduct.objects.create(
            name='E2E Personal Loan',
            description='Lifecycle regression product',
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

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_client_onboarding_to_closed_loan_blocks_pre_disbursement_payment(self):
        register_response = self.client.post(
            '/api/v1/auth/register/',
            {
                'first_name': 'Lifecycle',
                'last_name': 'Client',
                'phone': '0971000001',
                'password': 'clientpass123',
                'email': 'lifecycle.client@example.com',
                'nrc_number': 'E2E-NRC-001',
                'monthly_income': '6000',
                'employment_status': 'EMPLOYED',
            },
            format='json',
        )
        self.assertEqual(register_response.status_code, 201, register_response.data)
        client_user = User.objects.get(username='0971000001')
        client_profile = Client.objects.get(user=client_user)
        self.assertFalse(client_profile.kyc_verified)

        submission = KYCSubmission.objects.get(client=client_profile)
        self._auth(self.admin)
        kyc_response = self.client.patch(
            f'/api/v1/kyc/submissions/{submission.id}/',
            {'status': 'APPROVED', 'reviewer_notes': 'Documents verified.'},
            format='json',
        )
        self.assertEqual(kyc_response.status_code, 200, kyc_response.data)
        client_profile.refresh_from_db()
        self.assertTrue(client_profile.kyc_verified)

        qualified_response = self.client.post(
            '/api/v1/qualified-base/from-client/',
            {
                'client_id': client_profile.id,
                'amount_qualified_for': '3000',
                'reason': 'E2E affordability check passed.',
                'product_name': self.product.name,
            },
            format='json',
        )
        self.assertEqual(qualified_response.status_code, 201, qualified_response.data)

        self._auth(client_user)
        application_response = self.client.post(
            '/api/v1/loans/',
            {
                'product': self.product.id,
                'amount': '1000',
                'purpose': 'School fees',
                'term_months': 1,
                'documents': [],
            },
            format='json',
        )
        self.assertEqual(application_response.status_code, 201, application_response.data)
        loan = Loan.objects.get(client=client_profile)
        loan_id = loan.id
        self.assertEqual(loan.client_id, client_profile.id)
        self.assertEqual(loan.status, LoanStatus.PENDING_APPROVAL)

        self._auth(self.underwriter)
        approve_response = self.client.post(
            f'/api/v1/loans/{loan_id}/approve/',
            {'comments': 'Approved after E2E review.'},
            format='json',
        )
        self.assertEqual(approve_response.status_code, 200, approve_response.data)
        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanStatus.APPROVED)
        self.assertIsNone(loan.disbursement_date)

        self._auth(client_user)
        blocked_payment_response = self.client.post(
            f'/api/v1/loans/{loan_id}/repay/',
            {'amount': '100', 'notes': 'Should be blocked before disbursement.'},
            format='json',
        )
        self.assertEqual(blocked_payment_response.status_code, 400, blocked_payment_response.data)
        self.assertIn('active or overdue', blocked_payment_response.data['error'])
        loan.refresh_from_db()
        self.assertEqual(loan.repaid_amount, 0)
        self.assertFalse(loan.transactions.filter(transaction_type=TransactionType.REPAYMENT).exists())

        self._auth(self.accountant)
        disburse_response = self.client.post(f'/api/v1/loans/{loan_id}/disburse/', {}, format='json')
        self.assertEqual(disburse_response.status_code, 200, disburse_response.data)
        loan.refresh_from_db()
        self.assertEqual(loan.status, LoanStatus.ACTIVE)
        self.assertIsNotNone(loan.disbursement_date)

        self._auth(client_user)
        close_response = self.client.post(
            f'/api/v1/loans/{loan_id}/repay/',
            {'amount': str(loan.total_repayable), 'notes': 'Final repayment.'},
            format='json',
        )
        self.assertEqual(close_response.status_code, 200, close_response.data)
        loan.refresh_from_db()
        client_profile.refresh_from_db()
        self.assertEqual(loan.status, LoanStatus.CLOSED)
        self.assertEqual(loan.repaid_amount, loan.total_repayable)
        self.assertEqual(client_profile.completed_loans, 1)

        duplicate_payment_response = self.client.post(
            f'/api/v1/loans/{loan_id}/repay/',
            {'amount': '1', 'notes': 'Should be blocked after closure.'},
            format='json',
        )
        self.assertEqual(duplicate_payment_response.status_code, 400, duplicate_payment_response.data)
        self.assertIn('active or overdue', duplicate_payment_response.data['error'])
        client_profile.refresh_from_db()
        self.assertEqual(client_profile.completed_loans, 1)
