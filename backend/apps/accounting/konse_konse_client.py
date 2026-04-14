# -*- coding: utf-8 -*-
"""
konse_konse_client.py
=====================
HTTP client for the Konse Konse (*543#) USSD payment gateway used by
IntZam Microfinance / CirclePay Zambia.

Architecture overview
---------------------
Konse Konse is Zambia's shared USSD shortcode (*543#) that allows customers
to disburse and repay loans via any mobile network (MTN, Airtel, Zamtel).

This module provides a single ``KonseKonseClient`` class that:

1. Loads connection parameters from environment variables (never hard-coded).
2. Builds a ``requests.Session`` with HMAC-SHA256 request signing on every
   call — Konse Konse rejects unsigned requests.
3. Retries on transient failures (5xx, ConnectionError, Timeout) with
   exponential back-off.  4xx errors are never retried (they indicate a
   client-side problem and retrying would just generate duplicate alerts).
4. Supports a ``KONSE_SANDBOX=true`` mode that switches the base URL to the
   Konse Konse sandbox endpoint automatically — no code changes needed for
   staging vs. production.

Endpoints used
--------------
POST  {base}/api/v1/disburse          — push funds to borrower mobile wallet
POST  {base}/api/v1/collect           — pull repayment / fee from borrower
GET   {base}/api/v1/transaction/{ref} — poll status of any prior transaction

Request structure
-----------------
All POST bodies are JSON::

    {
        "merchantRef":  "<LMS loan_number>-<timestamp>",
        "amount":       "1500.00",
        "currency":     "ZMW",
        "mobileNumber": "0971234567",
        "narration":    "Loan disbursement LN123456",
        "signature":    "<HMAC-SHA256 hex digest>"
    }

Response structure (normalised by this client)::

    {
        "success":   true,
        "reference": "KK-20260316-ABC123",
        "status":    "PENDING" | "CONFIRMED" | "FAILED" | "REVERSED",
        "message":   "...",
        "data":      { ... }   # raw KK payload preserved for debugging
    }

Environment variables
---------------------
KONSE_BASE_URL          Live endpoint, e.g. https://api.konsepay.com
KONSE_API_KEY           API key issued by Konse Konse
KONSE_SECRET            HMAC signing secret (keep in .env, never in code)
KONSE_SANDBOX           "true" to use sandbox; any other value = production
KONSE_MAX_RETRIES       Number of retry attempts on 5xx/timeout (default 3)
KONSE_WEBHOOK_SECRET    Separate secret used to validate inbound webhooks
                        (not used here — see views.py)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# ── Load .env (same pattern as odoo_client.py) ────────────────────────────────
_ENV_PATH = Path(__file__).resolve().parents[2] / '.env'
load_dotenv(_ENV_PATH, override=False)

_logger = logging.getLogger(__name__)

# Konse Konse sandbox base URL
_SANDBOX_BASE_URL = 'https://sandbox.konsepay.com'

# Status constants mirroring the Konse Konse API documentation
STATUS_PENDING   = 'PENDING'
STATUS_CONFIRMED = 'CONFIRMED'
STATUS_FAILED    = 'FAILED'
STATUS_REVERSED  = 'REVERSED'


# ── Custom exceptions ──────────────────────────────────────────────────────────

class KonseConnectionError(IOError):
    """Raised when the Konse Konse gateway cannot be reached (network/DNS/TLS)."""


class KonseAuthError(PermissionError):
    """Raised on 401/403 responses — bad API key or invalid HMAC signature."""


class KonseAPIError(RuntimeError):
    """Raised when Konse Konse returns a non-2xx status or success=false."""

    def __init__(self, message: str, status_code: int = 0, raw: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.raw = raw or {}


# ── Main client ───────────────────────────────────────────────────────────────

class KonseKonseClient:
    """
    HTTP client for the Konse Konse (*543#) payment gateway.

    Instantiate once per request or as a module-level singleton — the
    underlying ``requests.Session`` is thread-safe for reads.

    Example usage::

        client = KonseKonseClient()
        result = client.disburse_loan(
            loan_number   = 'LN123456',
            amount        = 1500.00,
            mobile_number = '0971234567',
            narration     = 'Loan disbursement LN123456',
        )
        if result['status'] == 'CONFIRMED':
            handle_disbursement_confirmed(result['reference'], loan, amount)
    """

    def __init__(self) -> None:
        """
        Load configuration from environment and build an authenticated session.

        Raises:
            KonseAuthError: If KONSE_API_KEY or KONSE_SECRET are not set and
                            KONSE_SANDBOX is not 'true'.
        """
        self.sandbox    = os.getenv('KONSE_SANDBOX', 'true').lower() == 'true'
        self.api_key    = os.getenv('KONSE_API_KEY', '')
        self.secret     = os.getenv('KONSE_SECRET', '')
        self.max_retries = int(os.getenv('KONSE_MAX_RETRIES', '3'))

        # Sandbox overrides base URL regardless of KONSE_BASE_URL setting
        if self.sandbox:
            self.base_url = _SANDBOX_BASE_URL
        else:
            self.base_url = os.getenv('KONSE_BASE_URL', _SANDBOX_BASE_URL).rstrip('/')

        if not self.sandbox and not self.api_key:
            raise KonseAuthError(
                'KONSE_API_KEY is not set. '
                'Set KONSE_SANDBOX=true or provide a valid API key.'
            )

        # Build session with default auth headers applied to every request
        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'Accept':       'application/json',
            'X-Api-Key':    self.api_key,
        })

        _logger.info(
            'KonseKonseClient initialised | sandbox=%s base_url=%s max_retries=%d',
            self.sandbox, self.base_url, self.max_retries,
        )

    # ── Public methods ─────────────────────────────────────────────────────────

    def disburse_loan(
        self,
        loan_number: str,
        amount: float,
        mobile_number: str,
        narration: str,
    ) -> dict:
        """
        Push loan disbursement funds to a borrower's mobile wallet.

        Args:
            loan_number:   LMS loan reference (used as merchantRef prefix).
            amount:        ZMW amount to disburse.
            mobile_number: Recipient mobile number (0971234567 format).
            narration:     Human-readable description shown to the recipient.

        Returns:
            dict with keys: reference, status, message
            status is one of PENDING | CONFIRMED | FAILED | REVERSED

        Raises:
            KonseConnectionError: Gateway unreachable.
            KonseAuthError:       Bad API key or HMAC.
            KonseAPIError:        Gateway returned an error response.
        """
        merchant_ref = f'{loan_number}-DISB-{int(time.time())}'
        payload = {
            'merchantRef':  merchant_ref,
            'amount':       f'{float(amount):.2f}',
            'currency':     'ZMW',
            'mobileNumber': mobile_number,
            'narration':    narration,
            'type':         'DISBURSEMENT',
        }
        payload['signature'] = self._sign_request(payload)

        _logger.info(
            'KK disburse_loan | loan=%s amount=%.2f mobile=%s merchantRef=%s',
            loan_number, amount, mobile_number, merchant_ref,
        )
        raw = self._post('/api/v1/disburse', payload)
        return self._normalise(raw)

    def collect_repayment(
        self,
        loan_number: str,
        amount: float,
        mobile_number: str,
        narration: str,
    ) -> dict:
        """
        Pull a repayment from a borrower's mobile wallet.

        Args:
            loan_number:   LMS loan reference.
            amount:        ZMW amount to collect.
            mobile_number: Payer mobile number.
            narration:     Description shown to the payer on USSD prompt.

        Returns:
            dict with keys: reference, status, message
        """
        merchant_ref = f'{loan_number}-REPY-{int(time.time())}'
        payload = {
            'merchantRef':  merchant_ref,
            'amount':       f'{float(amount):.2f}',
            'currency':     'ZMW',
            'mobileNumber': mobile_number,
            'narration':    narration,
            'type':         'REPAYMENT',
        }
        payload['signature'] = self._sign_request(payload)

        _logger.info(
            'KK collect_repayment | loan=%s amount=%.2f mobile=%s merchantRef=%s',
            loan_number, amount, mobile_number, merchant_ref,
        )
        raw = self._post('/api/v1/collect', payload)
        return self._normalise(raw)

    def collect_fee(
        self,
        loan_number: str,
        amount: float,
        mobile_number: str,
        fee_type: str,
        narration: str,
    ) -> dict:
        """
        Pull a loan fee (origination, application, etc.) from a borrower's wallet.

        Args:
            loan_number:   LMS loan reference.
            amount:        ZMW fee amount to collect.
            mobile_number: Payer mobile number.
            fee_type:      Fee category string, e.g. 'origination', 'application'.
            narration:     Description shown to the payer.

        Returns:
            dict with keys: reference, status, message
        """
        merchant_ref = f'{loan_number}-FEE-{fee_type.upper()}-{int(time.time())}'
        payload = {
            'merchantRef':  merchant_ref,
            'amount':       f'{float(amount):.2f}',
            'currency':     'ZMW',
            'mobileNumber': mobile_number,
            'narration':    narration,
            'type':         'FEE',
            'feeType':      fee_type.upper(),
        }
        payload['signature'] = self._sign_request(payload)

        _logger.info(
            'KK collect_fee | loan=%s amount=%.2f fee_type=%s mobile=%s',
            loan_number, amount, fee_type, mobile_number,
        )
        raw = self._post('/api/v1/collect', payload)
        return self._normalise(raw)

    def collect_agent(
        self,
        loan_number: str,
        amount: float,
        agent_code: str,
        mobile_number: str,
        narration: str,
    ) -> dict:
        """
        Record a collection made by a field agent on the USSD platform.

        Args:
            loan_number:   LMS loan reference.
            amount:        ZMW amount collected.
            agent_code:    IntZam agent identifier.
            mobile_number: Borrower mobile number.
            narration:     Description.

        Returns:
            dict with keys: reference, status, message
        """
        merchant_ref = f'{loan_number}-AGNT-{agent_code}-{int(time.time())}'
        payload = {
            'merchantRef':  merchant_ref,
            'amount':       f'{float(amount):.2f}',
            'currency':     'ZMW',
            'mobileNumber': mobile_number,
            'agentCode':    agent_code,
            'narration':    narration,
            'type':         'AGENT_COLLECTION',
        }
        payload['signature'] = self._sign_request(payload)

        _logger.info(
            'KK collect_agent | loan=%s amount=%.2f agent=%s mobile=%s',
            loan_number, amount, agent_code, mobile_number,
        )
        raw = self._post('/api/v1/collect', payload)
        return self._normalise(raw)

    def get_transaction_status(self, reference: str) -> dict:
        """
        Poll the status of a prior Konse Konse transaction by its reference.

        Used by the ``poll_konse_transactions`` management command to resolve
        PENDING transactions that did not receive a webhook callback.

        Args:
            reference: The KK transaction reference (e.g. 'KK-20260316-ABC123').

        Returns:
            dict with keys: reference, status, amount, timestamp, raw
        """
        _logger.debug('KK get_transaction_status | reference=%s', reference)
        url = f'{self.base_url}/api/v1/transaction/{reference}'
        try:
            resp = self._session.get(url, timeout=30)
        except (requests.ConnectionError, requests.Timeout) as exc:
            raise KonseConnectionError(
                f'Cannot reach Konse Konse gateway: {exc}'
            ) from exc

        if resp.status_code in (401, 403):
            raise KonseAuthError(
                f'Konse Konse authentication error on status poll: {resp.status_code}'
            )
        if not resp.ok:
            raise KonseAPIError(
                f'Unexpected status {resp.status_code} polling ref {reference}',
                status_code=resp.status_code,
                raw={'body': resp.text},
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise KonseAPIError(
                f'Invalid JSON response polling ref {reference}: {exc}',
                raw={'body': resp.text},
            ) from exc

        return {
            'reference': data.get('reference', reference),
            'status':    data.get('status', STATUS_PENDING),
            'amount':    data.get('amount'),
            'timestamp': data.get('timestamp'),
            'raw':       data,
        }

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _post(self, endpoint: str, payload: dict) -> dict:
        """
        POST JSON payload to a Konse Konse endpoint with retry logic.

        Retry policy:
          - Retries on: 5xx responses, ConnectionError, Timeout
          - Never retries on: 4xx (client errors — retrying causes duplicates)
          - Back-off: 2^attempt seconds (1s, 2s, 4s, ...)

        Args:
            endpoint: Path starting with '/', e.g. '/api/v1/disburse'.
            payload:  Dict to serialise as JSON body.

        Returns:
            Parsed JSON response dict.

        Raises:
            KonseConnectionError: After all retries exhausted on network errors.
            KonseAuthError:       On 401/403.
            KonseAPIError:        On non-2xx after retries, or success=false.
        """
        url  = f'{self.base_url}{endpoint}'
        body = json.dumps(payload, default=str)

        last_exc: Exception | None = None

        for attempt in range(self.max_retries + 1):
            if attempt > 0:
                sleep_secs = 2 ** (attempt - 1)   # 1s, 2s, 4s
                _logger.warning(
                    'KK retry %d/%d for %s (backoff %ds)',
                    attempt, self.max_retries, endpoint, sleep_secs,
                )
                time.sleep(sleep_secs)

            try:
                resp = self._session.post(url, data=body, timeout=30)
            except (requests.ConnectionError, requests.Timeout) as exc:
                last_exc = exc
                _logger.warning('KK connection error attempt %d: %s', attempt, exc)
                continue   # retry

            # 4xx — do not retry
            if resp.status_code in (401, 403):
                raise KonseAuthError(
                    f'Konse Konse auth error {resp.status_code} on {endpoint}: {resp.text}'
                )
            if 400 <= resp.status_code < 500:
                try:
                    data = resp.json()
                except ValueError:
                    data = {'body': resp.text}
                raise KonseAPIError(
                    f'Konse Konse client error {resp.status_code} on {endpoint}: {resp.text}',
                    status_code=resp.status_code,
                    raw=data,
                )

            # 5xx — retry
            if resp.status_code >= 500:
                last_exc = KonseAPIError(
                    f'Konse Konse server error {resp.status_code}',
                    status_code=resp.status_code,
                )
                continue

            # 2xx — parse and validate
            try:
                data = resp.json()
            except ValueError as exc:
                raise KonseAPIError(
                    f'Invalid JSON from Konse Konse on {endpoint}: {resp.text}',
                    raw={'body': resp.text},
                ) from exc

            if not data.get('success', True):
                raise KonseAPIError(
                    data.get('message', 'Konse Konse returned success=false'),
                    status_code=resp.status_code,
                    raw=data,
                )

            _logger.info(
                'KK %s OK | ref=%s status=%s',
                endpoint, data.get('reference'), data.get('status'),
            )
            return data

        # All retries exhausted
        if last_exc is not None:
            if isinstance(last_exc, (requests.ConnectionError, requests.Timeout)):
                raise KonseConnectionError(
                    f'Cannot reach Konse Konse after {self.max_retries} retries: {last_exc}'
                ) from last_exc
            raise last_exc  # type: ignore[misc]

        raise KonseConnectionError(
            f'Konse Konse call to {endpoint} failed after {self.max_retries} retries.'
        )

    def _sign_request(self, payload: dict) -> str:
        """
        Produce an HMAC-SHA256 hex-digest signature of the JSON-serialised payload.

        The signature is computed over the canonical JSON of the payload
        (sorted keys, no extra whitespace) using KONSE_SECRET as the key.
        The resulting hex string is added to the request body as ``signature``.

        Args:
            payload: Request body dict (without the ``signature`` key).

        Returns:
            Lowercase hex HMAC-SHA256 digest string.
        """
        # Exclude 'signature' itself if accidentally present
        signing_payload = {k: v for k, v in payload.items() if k != 'signature'}
        canonical = json.dumps(signing_payload, sort_keys=True, separators=(',', ':'))
        digest = hmac.new(
            self.secret.encode('utf-8'),
            canonical.encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()
        return digest

    @staticmethod
    def _normalise(raw: dict) -> dict:
        """
        Normalise a raw KK API response to a consistent return shape.

        Args:
            raw: Parsed JSON dict from the KK API.

        Returns:
            dict with keys: reference, status, message
        """
        return {
            'reference': raw.get('reference', ''),
            'status':    raw.get('status', STATUS_PENDING),
            'message':   raw.get('message', ''),
        }
