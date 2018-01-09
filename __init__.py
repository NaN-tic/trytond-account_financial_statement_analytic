# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import report


def register():
    Pool.register(
        report.Report,
        report.ReportLine,
        report.Line,
        module='account_financial_statement_analytic', type_='model')
