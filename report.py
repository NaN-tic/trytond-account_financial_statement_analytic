# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
from sql import Column, Null
from sql.aggregate import Sum
from sql.conditionals import Coalesce

from trytond.model import fields, ModelSQL
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Bool, Eval, If
from trytond.modules.account_financial_statement.report import _STATES


class ReportAnalyticAccounts(ModelSQL):
    "Report Analytic Accounts"
    __name__ = 'account.financial.statement.report-analytic_account.account'

    report = fields.Many2One('account.financial.statement.report', "Report",
        ondelete='CASCADE', required=True)
    account = fields.Many2One('analytic_account.account', "Analytic Account",
        ondelete='CASCADE', required=True)


class Report(metaclass=PoolMeta):
    __name__ = 'account.financial.statement.report'

    analytic_accounts = fields.Many2Many(
        'account.financial.statement.report-analytic_account.account',
        'report', 'account', 'Analytic Accounts',
        domain=[
            ('company', '=', Eval('company', -1)),
            If(Bool(Eval('analytic_accounts')),
                ('currency', '=', Eval('currency')),
                ())
            ],
        states=_STATES)
    currency = fields.Function(fields.Many2One('currency.currency',
        'Currency'), 'on_change_with_currency')
    #currency = fields.Function(fields.Many2One('currency.currency',
    #    'Currency'), 'on_change_with_currency', searcher='search_currency')

    @classmethod
    def __register__(cls, module_name):
        pool = Pool()
        ReportAnalytic = pool.get(
            'account.financial.statement.report-analytic_account.account')

        sql_table = cls.__table__()
        report_analytic_table = ReportAnalytic.__table__()
        table = cls.__table_handler__(module_name)

        transaction = Transaction()
        cursor = transaction.connection.cursor()

        exist = table.column_exist('analytic_account')

        super().__register__(module_name)

        if exist:
            cursor.execute(*report_analytic_table.insert(
                    columns=[report_analytic_table.report,
                        report_analytic_table.account],
                    values=sql_table.select(sql_table.id,
                        sql_table.analytic_account,
                        where=sql_table.analytic_account != Null)))
            table.drop_column('analytic_account')

    @fields.depends('company')
    def on_change_with_currency(self, name=None):
        return self.company.currency if self.company else None

    #@classmethod
    #def search_currency(cls, name, clause):
    #    nested = clause[0][len(name) + 1:]
    #    return [('company.currency' + nested, *clause[1:])]


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
        analytic_accounts = self.report.analytic_accounts
        if not analytic_accounts:
            return super(ReportLine, self)._get_credit_debit(accounts)
        analytic_currency = self.report.currency

        account_ids = [x.id for x in accounts]
        # Get analytic credit, debit grouped by account.account
        result = {
            'debit': {}.fromkeys(account_ids, Decimal(0)),
            'credit': {}.fromkeys(account_ids, Decimal(0)),
            }
        id2account = {}
        for account in Analytic.search([
                    ('parent', 'child_of', [a.id for a in analytic_accounts]),
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
                            analytic_currency[0].currency, round=True)
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
