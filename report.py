# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
from sql import Column
from sql.aggregate import Sum
from sql.conditionals import Coalesce

from trytond.model import fields
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.modules.account_financial_statement.report import _STATES,\
    _DEPENDS

__all__ = ['Report', 'ReportLine', 'Line']


class Report(metaclass=PoolMeta):
    __name__ = 'account.financial.statement.report'

    analytic_account = fields.Many2One('analytic_account.account',
        'Analytic Account', states=_STATES, depends=_DEPENDS)


class ReportLine(metaclass=PoolMeta):
    __name__ = 'account.financial.statement.report.line'

    def _get_credit_debit(self, accounts):
        pool = Pool()
        Analytic = pool.get('analytic_account.account')
        Line = pool.get('analytic_account.line')
        MoveLine = pool.get('account.move.line')
        Account = pool.get('account.account')
        Company = pool.get('company.company')
        Currency = pool.get('currency.currency')
        cursor = Transaction().connection.cursor()
        table = Analytic.__table__()
        line = Line.__table__()
        move_line = MoveLine.__table__()
        a_account = Account.__table__()
        company = Company.__table__()
        analytic_account = self.report.analytic_account
        if not analytic_account:
            return super(ReportLine, self)._get_credit_debit(accounts)

        account_ids = [x.id for x in accounts]
        # Get analytic credit, debit grouped by account.account
        result = {
            'debit': {}.fromkeys(account_ids, Decimal('0.0')),
            'credit': {}.fromkeys(account_ids, Decimal('0.0')),
            }
        id2account = {}
        for account in Analytic.search([
                    ('parent', 'child_of', analytic_account.id),
                    ]):
            id2account[account.id] = account

        line_query = Line.query_get(line)
        cursor.execute(*table.join(line, 'LEFT',
                condition=table.id == line.account
                ).join(move_line, 'LEFT',
                condition=move_line.id == line.move_line
                ).join(a_account, 'LEFT',
                condition=a_account.id == move_line.account
                ).join(company, 'LEFT',
                condition=company.id == a_account.company
                ).select(table.id, move_line.account,
                company.currency,
                Sum(Coalesce(Column(line, 'credit'), 0)),
                Sum(Coalesce(Column(line, 'debit'), 0)),
                where=(table.type != 'view')
                & (table.id.in_(list(id2account.keys())))
                & table.active & line_query & (move_line.account.in_(
                        account_ids)),
                group_by=(table.id, move_line.account, company.currency)))

        id2currency = {}
        for row in cursor.fetchall():
            analytic = id2account[row[0]]
            account_id = row[1]
            currency_id = row[2]
            for i, name in enumerate(['credit', 'debit'], 3):
                # SQLite uses float for SUM
                sum = row[i]
                if not isinstance(sum, Decimal):
                    sum = Decimal(str(sum))
                if currency_id != analytic.currency.id:
                    currency = None
                    if currency_id in id2currency:
                        currency = id2currency[currency_id]
                    else:
                        currency = Currency(currency_id)
                        id2currency[currency.id] = currency
                    result[name][account_id] += Currency.compute(currency, sum,
                            analytic_account.currency, round=True)
                else:
                    result[name][account_id] += (analytic.currency.round(sum))
        return result


class Line(metaclass=PoolMeta):
    __name__ = 'analytic_account.line'

    @classmethod
    def query_get(cls, table):
        pool = Pool()
        MoveLine = pool.get('account.move.line')
        line = MoveLine.__table__()
        clause = super(Line, cls).query_get(table)
        context = Transaction().context
        filter_keys = ['date', 'posted', 'periods', 'fiscalyear', 'accounts']
        if any(x in context for x in filter_keys):
            line_clause, _ = MoveLine.query_get(line)
            clause = clause & table.move_line.in_(
                line.select(line.id, where=line_clause))
        return clause
