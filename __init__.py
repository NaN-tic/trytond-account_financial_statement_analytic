# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from .report import *


def register():
    Pool.register(
        Report,
        ReportLine,
        Line,
        module='account_financial_statement_analytic', type_='model')
