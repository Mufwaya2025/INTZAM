from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.conf import settings
from apps.loans.models import Loan
from apps.core.models import Client


class AIRiskAnalysisView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, loan_id):
        try:
            loan = Loan.objects.select_related('client', 'product').get(pk=loan_id)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)

        client = loan.client
        analysis = self._analyze_risk(loan, client)
        return Response({'analysis': analysis})

    def _analyze_risk(self, loan, client):
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return self._mock_analysis(loan, client)

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')

            prompt = f"""
You are an expert loan underwriter for IntZam Micro Fin Limited. Analyze the following loan application and provide a detailed risk assessment.

**Loan Application Details:**
- Loan Number: {loan.loan_number}
- Amount Requested: ${float(loan.amount):,.2f}
- Term: {loan.term_months} months
- Interest Rate: {float(loan.interest_rate)}%
- Purpose: {loan.purpose}
- Product: {loan.product.name}

**Client Profile:**
- Name: {client.name}
- Employment Status: {client.employment_status}
- Monthly Income: ${float(client.monthly_income):,.2f}
- Credit Score: {client.credit_score}
- Loyalty Tier: {client.tier}
- Completed Loans: {client.completed_loans}
- KYC Verified: {client.kyc_verified}

**Calculations:**
- Monthly Payment: ${float(loan.monthly_payment):,.2f}
- Total Repayable: ${float(loan.total_repayable):,.2f}
- Debt-to-Income Ratio: {(float(loan.monthly_payment) / float(client.monthly_income) * 100) if float(client.monthly_income) > 0 else 'N/A'}%

Please provide:
1. **Risk Rating**: LOW / MEDIUM / HIGH
2. **Recommendation**: APPROVE / REJECT / REVIEW
3. **Key Risk Factors** (bullet points)
4. **Strengths** (bullet points)
5. **Conditions** (if any, for approval)
6. **Summary** (2-3 sentences)

Format your response in clear markdown.
"""
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return self._mock_analysis(loan, client)

    def _mock_analysis(self, loan, client):
        dti = (float(loan.monthly_payment) / float(client.monthly_income) * 100) if float(client.monthly_income) > 0 else 0
        risk = 'LOW' if dti < 30 and client.credit_score > 600 else ('HIGH' if dti > 50 else 'MEDIUM')
        recommendation = 'APPROVE' if risk == 'LOW' else ('REJECT' if risk == 'HIGH' else 'REVIEW')

        return f"""## AI Risk Assessment

**Risk Rating:** {risk}
**Recommendation:** {recommendation}

### Key Risk Factors
- Debt-to-Income Ratio: {dti:.1f}%
- Credit Score: {client.credit_score}
- Employment: {client.employment_status}

### Strengths
- Client Tier: {client.tier}
- Completed Loans: {client.completed_loans}
- KYC Verified: {'Yes' if client.kyc_verified else 'No'}

### Summary
Based on the analysis, the client has a {risk.lower()} risk profile with a DTI of {dti:.1f}%. 
The recommendation is to **{recommendation}** this loan application.
{'Standard approval conditions apply.' if recommendation == 'APPROVE' else 'Additional documentation or collateral may be required.' if recommendation == 'REVIEW' else 'The application does not meet minimum criteria.'}
"""
