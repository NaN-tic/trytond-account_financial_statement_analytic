import unittest
from datetime import date
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import (
    create_chart,
    create_fiscalyear,
    get_accounts,
)
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.pool import Pool
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules
from trytond.transaction import Transaction


class TestFinancialStatementAnalyticMultiPeriod(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def create_move(self, period, amount, analytic_account=None):
        Move = Model.get('account.move', config=self.config)
        move = Move()
        move.journal = self.journal_revenue
        move.period = period
        move.date = period.start_date
        line = move.lines.new()
        line.account = self.revenue
        line.credit = amount
        if analytic_account:
            analytic_line = line.analytic_lines.new()
            analytic_line.account = analytic_account
            analytic_line.credit = amount
            analytic_line.date = period.start_date
        line = move.lines.new()
        line.account = self.receivable
        line.party = self.party
        line.debit = amount
        move.save()
        move.click('post')

    def setup_data(self):
        self.config = activate_modules('account_financial_statement_analytic')
        _ = create_company(config=self.config)
        self.company = get_company(config=self.config)
        create_chart(company=self.company, config=self.config)

        Party = Model.get('party.party', config=self.config)
        Journal = Model.get('account.journal', config=self.config)
        Period = Model.get('account.period', config=self.config)
        Template = Model.get('account.financial.statement.template',
            config=self.config)
        TemplateLine = Model.get('account.financial.statement.template.line',
            config=self.config)
        AnalyticAccount = Model.get('analytic_account.account', config=self.config)
        self.AnalyticAccount = AnalyticAccount

        accounts = get_accounts(company=self.company, config=self.config)
        self.revenue = accounts['revenue']
        self.receivable = accounts['receivable']
        self.journal_revenue, = Journal.find([('code', '=', 'REV')], limit=1)
        self.party = Party(name='Customer')
        self.party.save()

        self.analytic_root = AnalyticAccount(type='root', name='Root')
        self.analytic_root.save()
        self.analytic_account_a = AnalyticAccount(
            type='normal',
            name='Analytic A',
            parent=self.analytic_root,
            root=self.analytic_root)
        self.analytic_account_a.save()
        self.analytic_account_b = AnalyticAccount(
            type='normal',
            name='Analytic B',
            parent=self.analytic_root,
            root=self.analytic_root)
        self.analytic_account_b.save()

        self.fiscalyears = []
        for year in (2022, 2023, 2024):
            fiscalyear = create_fiscalyear(
                company=self.company,
                today=(date(year, 1, 1), date(year, 12, 31)),
                config=self.config)
            fiscalyear.save()
            fiscalyear.click('create_period')
            self.fiscalyears.append(fiscalyear)

        self.create_move(self.fiscalyears[0].periods[0], Decimal('10'),
            self.analytic_account_a)
        self.create_move(self.fiscalyears[1].periods[0], Decimal('20'),
            self.analytic_account_a)
        self.create_move(self.fiscalyears[2].periods[0], Decimal('30'),
            self.analytic_account_b)

        self.adjustment_period = Period()
        self.adjustment_period.name = 'Closing'
        self.adjustment_period.start_date = self.fiscalyears[0].end_date
        self.adjustment_period.end_date = self.fiscalyears[0].end_date
        self.adjustment_period.fiscalyear = self.fiscalyears[0]
        self.adjustment_period.type = 'adjustment'
        self.adjustment_period.save()
        self.create_move(self.adjustment_period, Decimal('40'),
            self.analytic_account_a)

        self.template = Template()
        self.template.name = 'Analytic Template'
        self.template.mode = 'credit-debit'
        line = self.template.lines.new()
        line.code = '0'
        line.name = 'Results'
        self.template.save()

        revenue_line = TemplateLine()
        revenue_line.template = self.template
        revenue_line.parent = self.template.lines[0]
        revenue_line.code = 'R'
        revenue_line.name = 'Revenue'
        revenue_line.current_value = 'balance("%s")' % self.revenue.code
        revenue_line.save()

    def test(self):
        self.setup_data()
        Report = Model.get('account.financial.statement.report',
            config=self.config)

        analytic_report = Report()
        analytic_report.name = 'Analytic Report'
        analytic_report.template = self.template
        analytic_report.analytic_accounts.append(
            self.AnalyticAccount(self.analytic_account_a.id))
        for fiscalyear in self.fiscalyears:
            period = analytic_report.comparison_periods.new()
            period.fiscalyear = fiscalyear
        analytic_report.save()
        analytic_report.click('calculate')

        analytic_parent_report = Report()
        analytic_parent_report.name = 'Analytic Parent Report'
        analytic_parent_report.template = self.template
        analytic_parent_report.analytic_accounts.append(
            self.AnalyticAccount(self.analytic_root.id))
        for fiscalyear in self.fiscalyears:
            period = analytic_parent_report.comparison_periods.new()
            period.fiscalyear = fiscalyear
        analytic_parent_report.save()
        analytic_parent_report.click('calculate')

        analytic_ranged_standard_report = Report()
        analytic_ranged_standard_report.name = 'Analytic Ranged Standard Report'
        analytic_ranged_standard_report.template = self.template
        analytic_ranged_standard_report.analytic_accounts.append(
            self.AnalyticAccount(self.analytic_account_a.id))
        analytic_ranged_standard_period = (
            analytic_ranged_standard_report.comparison_periods.new())
        analytic_ranged_standard_period.fiscalyear = self.fiscalyears[0]
        standard_periods = [
            period for period in self.fiscalyears[0].periods
            if period.type == 'standard']
        analytic_ranged_standard_period.start_period = standard_periods[0]
        analytic_ranged_standard_period.end_period = standard_periods[-1]
        analytic_ranged_standard_report.save()
        analytic_ranged_standard_report.click('calculate')

        analytic_ranged_adjustment_report = Report()
        analytic_ranged_adjustment_report.name = 'Analytic Ranged Adjustment Report'
        analytic_ranged_adjustment_report.template = self.template
        analytic_ranged_adjustment_report.analytic_accounts.append(
            self.AnalyticAccount(self.analytic_account_a.id))
        analytic_ranged_adjustment_period = (
            analytic_ranged_adjustment_report.comparison_periods.new())
        analytic_ranged_adjustment_period.fiscalyear = self.fiscalyears[0]
        analytic_ranged_adjustment_period.start_period = standard_periods[0]
        analytic_ranged_adjustment_period.end_period = self.adjustment_period
        analytic_ranged_adjustment_report.save()
        analytic_ranged_adjustment_report.click('calculate')

        pool = Pool(self.config.database_name)
        ReportModel = pool.get('account.financial.statement.report')

        with Transaction().start(
                self.config.database_name, self.config.user,
                context=self.config.context):
            analytic_report_record = ReportModel(analytic_report.id)
            analytic_parent_report_record = ReportModel(analytic_parent_report.id)
            analytic_ranged_standard_report_record = ReportModel(
                analytic_ranged_standard_report.id)
            analytic_ranged_adjustment_report_record = ReportModel(
                analytic_ranged_adjustment_report.id)

            analytic_period_values = {}
            for period in analytic_report_record.comparison_periods:
                revenue_line, = [line for line in period.lines if line.code == 'R']
                analytic_period_values[period.fiscalyear.id] = revenue_line.value
            self.assertEqual(analytic_period_values, {
                    self.fiscalyears[0].id: Decimal('10.00'),
                    self.fiscalyears[1].id: Decimal('20.00'),
                    self.fiscalyears[2].id: Decimal('0.00'),
                    })

            first_analytic_period, = [
                period for period in analytic_report_record.comparison_periods
                if period.fiscalyear.id == self.fiscalyears[0].id]
            analytic_revenue_line, = [
                line for line in first_analytic_period.lines if line.code == 'R']
            self.assertEqual(
                {(detail.debit, detail.credit, detail.balance)
                    for detail in analytic_revenue_line.line_accounts},
                {(Decimal('0.00'), Decimal('10.00'), Decimal('-10.00'))})

            analytic_parent_period_values = {}
            for period in analytic_parent_report_record.comparison_periods:
                revenue_line, = [line for line in period.lines if line.code == 'R']
                analytic_parent_period_values[period.fiscalyear.id] = (
                    revenue_line.value)
            self.assertEqual(analytic_parent_period_values, {
                    self.fiscalyears[0].id: Decimal('10.00'),
                    self.fiscalyears[1].id: Decimal('20.00'),
                    self.fiscalyears[2].id: Decimal('30.00'),
                    })

            analytic_ranged_standard_period_record, = (
                analytic_ranged_standard_report_record.comparison_periods)
            analytic_ranged_standard_revenue_line, = [
                line for line in analytic_ranged_standard_period_record.lines
                if line.code == 'R']
            self.assertEqual(
                analytic_ranged_standard_revenue_line.value, Decimal('10.00'))

            analytic_ranged_adjustment_period_record, = (
                analytic_ranged_adjustment_report_record.comparison_periods)
            analytic_ranged_adjustment_revenue_line, = [
                line for line in analytic_ranged_adjustment_period_record.lines
                if line.code == 'R']
            self.assertEqual(
                analytic_ranged_adjustment_revenue_line.value, Decimal('50.00'))
