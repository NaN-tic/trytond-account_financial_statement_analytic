# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
from decimal import Decimal

import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase, with_transaction
from trytond.pool import Pool

from trytond.modules.company.tests import create_company, set_company
from trytond.modules.account.tests import create_chart, get_fiscalyear


class TestCase(ModuleTestCase):
    '''
    Test module.
    '''
    module = 'account_financial_statement_analytic'

    def create_moves(self, company):
        pool = Pool()
        Party = pool.get('party.party')
        Party_address = pool.get('party.address')
        Move = pool.get('account.move')
        Account = pool.get('account.account')
        Journal = pool.get('account.journal')

        # Create Chart of Accounts and Fiscalyear
        create_chart(company)
        fiscalyear = get_fiscalyear(company)
        fiscalyear.save()
        fiscalyear.create_period([fiscalyear])
        period = fiscalyear.periods[0]
        last_period = fiscalyear.periods[-1]
        journal_revenue, = Journal.search([
                ('code', '=', 'REV'),
                ])
        journal_expense, = Journal.search([
                ('code', '=', 'EXP'),
                ])
        revenue, = Account.search([
                ('type.revenue', '=', True),
                ])
        Account.write([revenue], {'code': '7'})
        receivable, = Account.search([
                ('type.receivable', '=', True),
                ])
        Account.write([receivable], {'code': '43'})
        expense, = Account.search([
                ('type.expense', '=', True),
                ])
        Account.write([expense], {'code': '6'})
        payable, = Account.search([
                ('type.payable', '=', True),
                ])
        Account.write([payable], {'code': '41'})
        chart, = Account.search([
                ('parent', '=', None),
                ], limit=1)
        Account.create([{
                    'name': 'View',
                    'code': '1',
                    'parent': chart.id,
                    }])

        # Create some parties
        customer1, customer2, supplier1, supplier2 = Party.create([{
                        'name': 'customer1',
                    }, {
                        'name': 'customer2',
                    }, {
                        'name': 'supplier1',
                    }, {
                        'name': 'supplier2',
                    }])
        Party_address.create([{
                        'active': True,
                        'party': customer1.id,
                    }, {
                        'active': True,
                        'party': supplier1.id,
                    }])

        # Create some moves
        vlist = [
            {
                'period': period.id,
                'journal': journal_revenue.id,
                'date': period.start_date,
                'lines': [
                    ('create', [{
                                'account': revenue.id,
                                'credit': Decimal(100),
                                }, {
                                'party': customer1.id,
                                'account': receivable.id,
                                'debit': Decimal(100),
                                }]),
                    ],
                },
            {
                'period': period.id,
                'journal': journal_revenue.id,
                'date': period.start_date,
                'lines': [
                    ('create', [{
                                'account': revenue.id,
                                'credit': Decimal(200),
                                }, {
                                'party': customer2.id,
                                'account': receivable.id,
                                'debit': Decimal(200),
                                }]),
                    ],
                },
            {
                'period': period.id,
                'journal': journal_expense.id,
                'date': period.start_date,
                'lines': [
                    ('create', [{
                                'account': expense.id,
                                'debit': Decimal(30),
                                }, {
                                'party': supplier1.id,
                                'account': payable.id,
                                'credit': Decimal(30),
                                }]),
                    ],
                },
            {
                'period': period.id,
                'journal': journal_expense.id,
                'date': period.start_date,
                'lines': [
                    ('create', [{
                                'account': expense.id,
                                'debit': Decimal(50),
                                }, {
                                'party': supplier2.id,
                                'account': payable.id,
                                'credit': Decimal(50),
                                }]),
                    ],
                },
            {
                'period': last_period.id,
                'journal': journal_expense.id,
                'date': last_period.end_date,
                'lines': [
                    ('create', [{
                                'account': expense.id,
                                'debit': Decimal(50),
                                }, {
                                'party': supplier2.id,
                                'account': payable.id,
                                'credit': Decimal(50),
                                }]),
                    ],
                },
            {
                'period': last_period.id,
                'journal': journal_revenue.id,
                'date': last_period.end_date,
                'lines': [
                    ('create', [{
                                'account': revenue.id,
                                'credit': Decimal(300),
                                }, {
                                'party': customer2.id,
                                'account': receivable.id,
                                'debit': Decimal(300),
                                }]),
                    ],
                },
            ]
        moves = Move.create(vlist)
        Move.post(moves)

    @with_transaction()
    def test0010_with_analytic(self):
        pool = Pool()
        Party = pool.get('party.party')
        Account = pool.get('account.account')
        AnalyticAccount = pool.get('analytic_account.account')
        Fiscalyear = pool.get('account.fiscalyear')
        Move = pool.get('account.move')
        Journal = pool.get('account.journal')
        Template = pool.get('account.financial.statement.template')
        Report = pool.get('account.financial.statement.report')

        party = Party(name='Party')
        party.save()
        company = create_company()
        with set_company(company):
            self.create_moves(company)
            template, = Template.create([{
                        'name': 'Template',
                        'mode': 'credit-debit',
                        'lines': [('create', [{
                                        'code': '01',
                                        'name': 'Expense',
                                        'current_value': '6',
                                        'previous_value': '6',
                                        }, {
                                        'code': '02',
                                        'name': 'Revenue',
                                        'current_value': '7',
                                        'previous_value': '7',
                                        }]
                                )],
                        }])
            results = template.lines[0]
            root, = AnalyticAccount.create([{
                        'type': 'root',
                        'name': 'Root',
                        }])
            analytic_account, = AnalyticAccount.create([{
                        'type': 'normal',
                        'name': 'Analytic Account',
                        'parent': root.id,
                        'root': root.id,
                        }])
            fiscalyear, = Fiscalyear.search([])
            period = fiscalyear.periods[0]

            report, = Report.create([{
                        'name': 'Test report',
                        'template': template.id,
                        'current_fiscalyear': fiscalyear,
                        }])
            self.assertEqual(report.state, 'draft')
            Report.calculate([report])
            self.assertEqual(report.state, 'calculated')

            results = {
                '01': Decimal('-130.0'),
                '02': Decimal('600.0'),
                }
            for line in report.lines:
                self.assertEqual(line.previous_value, Decimal('0.0'))
                self.assertEqual(line.current_value, results[line.code])
            Report.draft([report])
            report.analytic_account = analytic_account
            report.save()
            Report.calculate([report])
            for line in report.lines:
                self.assertEqual(Decimal('0.0'), line.current_value)
                self.assertEqual(Decimal('0.0'), line.previous_value)

            # Create analytic moves and test their value
            journal_revenue, = Journal.search([
                    ('code', '=', 'REV'),
                    ])
            journal_expense, = Journal.search([
                    ('code', '=', 'EXP'),
                    ])
            revenue, = Account.search([
                    ('type.revenue', '=', True),
                    ])
            receivable, = Account.search([
                    ('type.receivable', '=', True),
                    ])
            expense, = Account.search([
                    ('type.expense', '=', True),
                    ])
            payable, = Account.search([
                    ('type.payable', '=', True),
                    ])
            first_account_line = {
                'account': revenue.id,
                'credit': Decimal(100),
                'analytic_lines': [
                    ('create', [{
                                'account': analytic_account.id,
                                'credit': Decimal(100),
                                'debit': Decimal(0),
                                'date': period.start_date,
                                }])
                    ]}
            second_account_line = {
                'account': expense.id,
                'debit': Decimal(30),
                'analytic_lines': [
                    ('create', [{
                                'account': analytic_account.id,
                                'debit': Decimal(30),
                                'credit': Decimal(0),
                                'date': period.start_date,
                                }])
                    ]}
            # Create some moves
            customer1, = Party.search([
                    ('name', '=', 'customer1'),
                    ])
            supplier1, = Party.search([
                    ('name', '=', 'supplier1'),
                    ])

            vlist = [{
                    'period': period.id,
                    'journal': journal_revenue.id,
                    'date': period.start_date,
                    'lines': [
                        ('create', [first_account_line, {
                                    'account': receivable.id,
                                    'debit': Decimal(100),
                                    'party': customer1.id,
                                    }]),
                        ],
                    }, {
                    'period': period.id,
                    'journal': journal_expense.id,
                    'date': period.start_date,
                    'lines': [
                        ('create', [second_account_line, {
                                    'account': payable.id,
                                    'credit': Decimal(30),
                                    'party': supplier1.id,
                                    }]),
                        ],
                    },
                ]
            Move.create(vlist)
            Report.draft([report])
            Report.calculate([report])
            results = {
                '01': Decimal('-30.0'),
                '02': Decimal('100.0'),
                }
            for line in report.lines:
                self.assertEqual(results[line.code], line.current_value)
                self.assertEqual(Decimal('0.0'), line.previous_value)
            Report.draft([report])
            report.analytic_account = root
            report.save()
            Report.calculate([report])
            for line in report.lines:
                self.assertEqual(results[line.code], line.current_value)
                self.assertEqual(Decimal('0.0'), line.previous_value)

    @with_transaction()
    def test0020_without_analytic(self):
        pool = Pool()
        Party = pool.get('party.party')
        Fiscalyear = pool.get('account.fiscalyear')
        Template = pool.get('account.financial.statement.template')
        Report = pool.get('account.financial.statement.report')
        TemplateLine = pool.get('account.financial.statement.template.line')

        party = Party(name='Party')
        party.save()
        company = create_company()
        with set_company(company):
            self.create_moves(company)
            template, = Template.create([{
                        'name': 'Template',
                        'mode': 'credit-debit',
                        'lines': [('create', [{
                                        'code': '0',
                                        'name': 'Results',
                                        }, {
                                        'code': '1',
                                        'name': 'Fixed',
                                        'current_value': '12.00',
                                        'previous_value': '10.00',
                                        }, {
                                        'code': '2',
                                        'name': 'Sum',
                                        'current_value': '0+1',
                                        'previous_value': '0+1',
                                        }]
                                )],
                        }])
            results = template.lines[0]
            # This must be created manually otherwise template is not set.
            TemplateLine.create([{
                            'code': '01',
                            'name': 'Expense',
                            'current_value': '6',
                            'previous_value': '6',
                            'parent': results.id,
                            'template': template.id,
                            }, {
                            'code': '02',
                            'name': 'Revenue',
                            'current_value': '7',
                            'previous_value': '7',
                            'parent': results.id,
                            'template': template.id,
                            }])
            fiscalyear, = Fiscalyear.search([])

            report, = Report.create([{
                        'name': 'Test report',
                        'template': template.id,
                        'current_fiscalyear': fiscalyear,
                        }])
            self.assertEqual(report.state, 'draft')
            Report.calculate([report])
            self.assertEqual(report.state, 'calculated')
            self.assertEqual(len(report.lines), 5)

            results = {
                '0': Decimal('470.0'),
                '1': Decimal('12.0'),
                '2': Decimal('482.0'),
                '01': Decimal('-130.0'),
                '02': Decimal('600.0'),
                }
            for line in report.lines:
                self.assertEqual(results[line.code], line.current_value)
                self.assertEqual(Decimal('0.0'), line.previous_value)


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    return suite
