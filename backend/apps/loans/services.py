from decimal import Decimal, ROUND_HALF_UP


MONEY_PRECISION = Decimal('0.01')
ONE = Decimal('1')
TWELVE = Decimal('12')
ONE_HUNDRED = Decimal('100')
ZERO = Decimal('0')


def _decimal(value) -> Decimal:
    if value in (None, ''):
        return ZERO
    return Decimal(str(value))


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PRECISION, rounding=ROUND_HALF_UP)


FREQUENCY_INSTALLMENTS_PER_MONTH = {
    'WEEKLY': 4,
    'BIWEEKLY': 2,
    'MONTHLY': 1,
}


def calculate_loan_terms(
    principal: float,
    interest_rate: float,
    term_months: int,
    interest_type: str,
    nominal_interest_rate: float | None = None,
    credit_facilitation_fee: float = 0,
    processing_fee: float = 0,
    repayment_frequency: str = 'MONTHLY',
) -> dict:
    """
    Calculate loan terms based on interest type.
    Returns: total_interest, total_repayable, monthly_payment, effective_rate, schedule
    """
    principal = _decimal(principal)
    total_rate = _decimal(interest_rate) / ONE_HUNDRED
    nominal_rate = _decimal(interest_rate if nominal_interest_rate is None else nominal_interest_rate) / ONE_HUNDRED
    facilitation_rate = _decimal(credit_facilitation_fee) / ONE_HUNDRED
    processing_rate = _decimal(processing_fee) / ONE_HUNDRED
    n = int(term_months)

    facilitation_fee_amount = principal * facilitation_rate
    processing_fee_amount = principal * processing_rate
    upfront_fees = facilitation_fee_amount + processing_fee_amount

    if interest_type == 'FLAT':
        if nominal_interest_rate is None:
            finance_interest = principal * total_rate
            facilitation_fee_amount = ZERO
            processing_fee_amount = ZERO
            upfront_fees = ZERO
        else:
            finance_interest = principal * nominal_rate
        total_interest = finance_interest + upfront_fees
        total_repayable = principal + total_interest
        monthly_payment = total_repayable / n
        effective_rate = float((total_interest / principal) * ONE_HUNDRED) if principal else 0

        schedule = []
        balance = principal
        monthly_principal = principal / n
        monthly_interest = total_interest / n
        for i in range(1, n + 1):
            balance -= monthly_principal
            schedule.append({
                'month': i,
                'payment': float(_money(monthly_payment)),
                'principal': float(_money(monthly_principal)),
                'interest': float(_money(monthly_interest)),
                'balance': float(_money(max(ZERO, balance))),
            })

    elif interest_type == 'REDUCING':
        monthly_rate = nominal_rate / Decimal(n) if n else ZERO
        if monthly_rate == 0:
            base_monthly_payment = principal / n
        else:
            growth_factor = (ONE + monthly_rate) ** n
            base_monthly_payment = principal * monthly_rate * growth_factor / (growth_factor - ONE)

        finance_total_repayable = base_monthly_payment * n
        finance_interest = finance_total_repayable - principal
        total_interest = finance_interest + upfront_fees
        total_repayable = principal + total_interest
        monthly_fee_share = upfront_fees / n
        monthly_payment = base_monthly_payment + monthly_fee_share
        effective_rate = float((total_interest / principal) * ONE_HUNDRED) if principal else 0

        schedule = []
        balance = principal
        for i in range(1, n + 1):
            interest = balance * monthly_rate
            principal_payment = base_monthly_payment - interest
            balance -= principal_payment
            schedule.append({
                'month': i,
                'payment': float(_money(monthly_payment)),
                'principal': float(_money(principal_payment)),
                'interest': float(_money(interest + monthly_fee_share)),
                'balance': float(_money(max(ZERO, balance))),
            })
    else:
        # Default to flat
        return calculate_loan_terms(
            float(principal),
            interest_rate,
            term_months,
            'FLAT',
            nominal_interest_rate=nominal_interest_rate,
            credit_facilitation_fee=credit_facilitation_fee,
            processing_fee=processing_fee,
        )

    # Adjust installment amount based on repayment frequency
    installments_per_month = FREQUENCY_INSTALLMENTS_PER_MONTH.get(repayment_frequency, 1)
    total_installments = n * installments_per_month
    installment_amount = _money(total_repayable / total_installments) if total_installments else monthly_payment

    return {
        'total_interest': float(_money(total_interest)),
        'finance_interest': float(_money(finance_interest)),
        'credit_facilitation_fee_amount': float(_money(facilitation_fee_amount)),
        'processing_fee_amount': float(_money(processing_fee_amount)),
        'total_repayable': float(_money(total_repayable)),
        'monthly_payment': float(installment_amount),
        'repayment_frequency': repayment_frequency,
        'total_installments': total_installments,
        'effective_rate': round(effective_rate, 2),
        'schedule': schedule,
    }


def calculate_rollover_fee(outstanding: float, rollover_rate: float, extension_days: int, default_days: int = 14) -> float:
    """Calculate rollover fee."""
    fixed_fee = 50
    ratio = extension_days / default_days
    interest_fee = outstanding * (rollover_rate / 100) * ratio
    return fixed_fee + interest_fee


def calculate_payoff_quote(loan) -> dict:
    """Calculate early settlement payoff quote."""
    from decimal import Decimal
    outstanding = float(loan.total_repayable) - float(loan.repaid_amount)
    # Early termination fee (2% of outstanding)
    early_termination_fee = outstanding * 0.02
    total_payoff = outstanding + early_termination_fee

    # Calculate interest saved
    remaining_months = loan.term_months - (float(loan.repaid_amount) / float(loan.monthly_payment) if float(loan.monthly_payment) > 0 else 0)
    interest_saved = remaining_months * float(loan.monthly_payment) * 0.3  # Approximate

    return {
        'principal_outstanding': outstanding,
        'early_termination_fee': early_termination_fee,
        'total_payoff_amount': total_payoff,
        'interest_saved': max(0, interest_saved),
    }


def check_rollover_eligibility(loan) -> dict:
    """Check if a loan is eligible for rollover."""
    product = loan.product
    if loan.rollover_count >= product.max_rollovers:
        return {'eligible': False, 'reason': f'Maximum rollovers ({product.max_rollovers}) reached'}

    if loan.status not in ['ACTIVE', 'OVERDUE']:
        return {'eligible': False, 'reason': 'Loan must be active or overdue'}

    required_paid = float(loan.amount) * (product.rollover_min_principal_paid_percent / 100)
    if float(loan.repaid_amount) < required_paid:
        return {
            'eligible': False,
            'reason': f'Must repay at least {product.rollover_min_principal_paid_percent}% of principal',
            'required': required_paid,
            'paid': float(loan.repaid_amount),
        }

    return {
        'eligible': True,
        'extension_days': product.rollover_extension_days,
        'rollover_rate': float(product.rollover_interest_rate),
        'rollovers_remaining': product.max_rollovers - loan.rollover_count,
    }
