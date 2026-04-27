from __future__ import annotations

import logging
import re
import uuid
from decimal import Decimal
from xml.etree import ElementTree
from xml.sax.saxutils import escape as xml_escape

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    CGRateServiceProvider,
    CGRateTransaction,
    CGRateTransactionStatus,
    CGRateTransactionType,
    Loan,
    LoanStatus,
    Transaction,
    TransactionType,
)

logger = logging.getLogger(__name__)


class CGRateError(RuntimeError):
    pass


def normalize_zambian_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone or '')
    if digits.startswith('260') and len(digits) == 12:
        return digits
    if digits.startswith('0') and len(digits) == 10:
        return '260' + digits[1:]
    if len(digits) == 9:
        return '260' + digits
    return digits


def detect_provider(phone: str) -> str:
    normalized = normalize_zambian_phone(phone)
    local = normalized[3:] if normalized.startswith('260') else normalized.lstrip('0')
    prefix = local[:2]
    if prefix in {'97', '75', '95', '99'}:
        return CGRateServiceProvider.AIRTEL
    return CGRateServiceProvider.MTN


class CGRatePaymentService:
    endpoint = getattr(settings, 'CGRATE_ENDPOINT', 'https://543.cgrate.co.zm/Konik/KonikWs')

    def __init__(self):
        self.username = getattr(settings, 'CGRATE_USERNAME', '')
        self.password = getattr(settings, 'CGRATE_PASSWORD', '')
        self.timeout = getattr(settings, 'CGRATE_TIMEOUT', 30)
        self.enabled = getattr(settings, 'CGRATE_ENABLED', False)

    def process_disbursement(self, loan: Loan) -> CGRateTransaction:
        existing = CGRateTransaction.objects.filter(
            loan=loan,
            transaction_type=CGRateTransactionType.DISBURSEMENT,
            status__in=[
                CGRateTransactionStatus.PENDING,
                CGRateTransactionStatus.PROCESSING,
                CGRateTransactionStatus.COMPLETED,
            ],
        ).first()
        if existing:
            return existing

        amount = Decimal(str(loan.amount))
        phone = normalize_zambian_phone(loan.client.phone)
        provider = detect_provider(phone)
        reference = self._reference('DISB', loan.loan_number)
        txn = CGRateTransaction.objects.create(
            loan=loan,
            transaction_type=CGRateTransactionType.DISBURSEMENT,
            name=loan.client.name,
            email=loan.client.email,
            phone_number=phone,
            amount=-amount,
            reference=reference,
            service=provider,
            status=CGRateTransactionStatus.PENDING,
        )
        return self._send_and_update(
            txn,
            self._build_disbursement_xml(amount, phone, provider, reference),
        )

    def process_collection(self, loan: Loan, amount: Decimal | float | str, note: str = '') -> CGRateTransaction:
        amount = Decimal(str(amount))
        phone = normalize_zambian_phone(loan.client.phone)
        provider = detect_provider(phone)
        reference = self._reference('PAY', loan.loan_number)
        txn = CGRateTransaction.objects.create(
            loan=loan,
            transaction_type=CGRateTransactionType.COLLECTION,
            name=loan.client.name,
            email=loan.client.email,
            phone_number=phone,
            amount=amount,
            reference=reference,
            service=provider,
            status=CGRateTransactionStatus.PENDING,
            response_message=note,
        )
        txn = self._send_and_update(
            txn,
            self._build_collection_xml(amount, phone, reference),
        )
        if txn.status == CGRateTransactionStatus.COMPLETED:
            self._apply_successful_collection(txn)
        return txn

    def check_payment_status(self, reference: str) -> dict:
        xml = self._build_status_xml(reference)
        raw = self._post(xml)
        parsed = self._parse_response(raw, expected='queryCustomerPaymentResponse')
        return {
            'success': parsed['response_code'] == '0',
            'status': CGRateTransactionStatus.COMPLETED if parsed['response_code'] == '0' else CGRateTransactionStatus.FAILED,
            'external_ref': parsed['external_ref'],
            'message': parsed['message'],
            'raw': raw,
        }

    def get_balance(self) -> dict:
        raw = self._post(self._build_balance_xml())
        root = ElementTree.fromstring(raw)
        balance = None
        for elem in root.iter():
            if elem.tag.split('}')[-1].lower() in {'balance', 'accountbalance'} and elem.text:
                balance = elem.text
                break
        return {'balance': float(balance) if balance is not None else None, 'raw': raw}

    def refresh_transaction_status(self, txn: CGRateTransaction) -> CGRateTransaction:
        if txn.status not in {CGRateTransactionStatus.PENDING, CGRateTransactionStatus.PROCESSING}:
            return txn
        try:
            result = self.check_payment_status(txn.reference)
        except Exception as exc:
            logger.exception('CGRate status check failed for %s', txn.reference)
            txn.response_message = str(exc)
            txn.save(update_fields=['response_message', 'updated_at'])
            return txn
        txn.status = result['status']
        txn.external_ref = result.get('external_ref') or txn.external_ref
        txn.response_message = result.get('message') or txn.response_message
        txn.raw_response = {'status_check': result.get('raw', '')}
        if txn.status in {CGRateTransactionStatus.COMPLETED, CGRateTransactionStatus.FAILED}:
            txn.processed_at = timezone.now()
        txn.save(update_fields=['status', 'external_ref', 'response_message', 'raw_response', 'processed_at', 'updated_at'])
        if txn.status == CGRateTransactionStatus.COMPLETED and txn.transaction_type == CGRateTransactionType.COLLECTION:
            self._apply_successful_collection(txn)
        return txn

    def _send_and_update(self, txn: CGRateTransaction, xml: str) -> CGRateTransaction:
        txn.status = CGRateTransactionStatus.PROCESSING
        txn.raw_request = {'soap': xml}
        txn.save(update_fields=['status', 'raw_request', 'updated_at'])
        logger.info('CGRate %s initiated ref=%s amount=%s phone=%s', txn.transaction_type, txn.reference, txn.amount, txn.phone_number)

        if not self.enabled:
            txn.status = CGRateTransactionStatus.PENDING
            txn.response_message = 'CGRate is disabled; transaction recorded for manual processing.'
            txn.save(update_fields=['status', 'response_message', 'updated_at'])
            return txn

        try:
            raw = self._post(xml)
            parsed = self._parse_response(raw)
            txn.raw_response = {'soap': raw}
            txn.external_ref = parsed['external_ref']
            txn.response_message = parsed['message']
            txn.status = (
                CGRateTransactionStatus.COMPLETED
                if parsed['response_code'] == '0'
                else CGRateTransactionStatus.FAILED
            )
            txn.processed_at = timezone.now()
            txn.save(update_fields=['raw_response', 'external_ref', 'response_message', 'status', 'processed_at', 'updated_at'])
            logger.info('CGRate %s finished ref=%s status=%s external_ref=%s', txn.transaction_type, txn.reference, txn.status, txn.external_ref)
        except Exception as exc:
            logger.exception('CGRate %s error ref=%s', txn.transaction_type, txn.reference)
            txn.status = CGRateTransactionStatus.ERROR
            txn.response_message = str(exc)
            txn.processed_at = timezone.now()
            txn.save(update_fields=['status', 'response_message', 'processed_at', 'updated_at'])
        return txn

    def _post(self, xml: str) -> str:
        if not self.username or not self.password:
            raise CGRateError('CGRATE_USERNAME and CGRATE_PASSWORD are required')
        response = requests.post(
            self.endpoint,
            data=xml.encode('utf-8'),
            headers={'Content-Type': 'text/xml; charset=utf-8'},
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise CGRateError(f'CGRate returned HTTP {response.status_code}: {response.text[:300]}')
        return response.text

    def _soap(self, body: str) -> str:
        return f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:kon="http://konik.cgrate.com">
   <soapenv:Header>
      <wsse:Security xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
         <wsse:UsernameToken>
            <wsse:Username>{self._x(self.username)}</wsse:Username>
            <wsse:Password>{self._x(self.password)}</wsse:Password>
         </wsse:UsernameToken>
      </wsse:Security>
   </soapenv:Header>
   <soapenv:Body>{body}</soapenv:Body>
</soapenv:Envelope>"""

    def _build_collection_xml(self, amount: Decimal, phone: str, reference: str) -> str:
        return self._soap(f"""<ns2:processCustomerPayment xmlns:ns2="http://konik.cgrate.com">
         <transactionAmount>{amount:.2f}</transactionAmount>
         <customerMobile>{self._x(phone)}</customerMobile>
         <paymentReference>{self._x(reference)}</paymentReference>
      </ns2:processCustomerPayment>""")

    def _build_disbursement_xml(self, amount: Decimal, phone: str, provider: str, reference: str) -> str:
        return self._soap(f"""<ns2:processCashDeposit xmlns:ns2="http://konik.cgrate.com">
         <transactionAmount>{amount:.2f}</transactionAmount>
         <customerAccount>{self._x(phone)}</customerAccount>
         <issuerName>{self._x(provider)}</issuerName>
         <depositorReference>{self._x(reference)}</depositorReference>
      </ns2:processCashDeposit>""")

    def _build_status_xml(self, reference: str) -> str:
        return self._soap(f"""<kon:queryCustomerPayment>
         <paymentReference>{self._x(reference)}</paymentReference>
      </kon:queryCustomerPayment>""")

    def _build_balance_xml(self) -> str:
        return self._soap('<kon:getAccountBalance></kon:getAccountBalance>')

    @staticmethod
    def _parse_response(xml: str, expected: str | None = None) -> dict:
        root = ElementTree.fromstring(xml)
        data = {'response_code': '', 'message': '', 'external_ref': ''}
        for elem in root.iter():
            name = elem.tag.split('}')[-1]
            text = elem.text or ''
            if name == 'responseCode':
                data['response_code'] = text.strip()
            elif name == 'responseMessage':
                data['message'] = text.strip()
            elif name in {'paymentID', 'paymentId', 'transactionID', 'transactionId'}:
                data['external_ref'] = text.strip()
        if not data['response_code']:
            raise CGRateError(f'CGRate response missing responseCode for {expected or "request"}')
        return data

    @staticmethod
    def _reference(prefix: str, loan_number: str) -> str:
        return f'{prefix}{loan_number}{uuid.uuid4().hex[:10].upper()}'

    @staticmethod
    def _x(value: object) -> str:
        return xml_escape(str(value or ''))

    @staticmethod
    def _apply_successful_collection(txn: CGRateTransaction) -> None:
        loan = txn.loan
        if not loan or loan.status not in {LoanStatus.ACTIVE, LoanStatus.OVERDUE}:
            return
        amount = abs(Decimal(str(txn.amount)))
        if loan.transactions.filter(reference=txn.reference).exists():
            return
        with transaction.atomic():
            loan = Loan.objects.select_for_update().get(pk=loan.pk)
            outstanding = Decimal(str(loan.total_repayable)) - Decimal(str(loan.repaid_amount))
            applied = min(amount, outstanding)
            if applied <= 0:
                return
            loan.repaid_amount = Decimal(str(loan.repaid_amount)) + applied
            if Decimal(str(loan.repaid_amount)) >= Decimal(str(loan.total_repayable)):
                loan.repaid_amount = loan.total_repayable
                loan.status = LoanStatus.CLOSED
                client = loan.client
                client.completed_loans += 1
                client.update_tier()
            loan.save()
            Transaction.objects.create(
                loan=loan,
                transaction_type=TransactionType.REPAYMENT,
                amount=applied,
                reference=txn.reference,
                posted_by='CGRate',
                notes=f'CGRate collection {txn.external_ref}'.strip(),
            )
