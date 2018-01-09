# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
try:
    from trytond.modules.account_financial_statement_analytic.tests.test_account_financial_statement_analytic import suite
except ImportError:
    from .test_account_financial_statement_analytic import suite

__all__ = ['suite']
