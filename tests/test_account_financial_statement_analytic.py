#!/usr/bin/env python
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import test_view, test_depends
from trytond.tests.test_tryton import POOL, DB_NAME, USER, CONTEXT
from trytond.transaction import Transaction


class TestCase(unittest.TestCase):
    '''
    Test module.
    '''

    def setUp(self):
        trytond.tests.test_tryton.install_module(
            'account_financial_statement_analytic')
        self.account = POOL.get('account.account')
        self.analytic_account = POOL.get('analytic_account.account')
        self.company = POOL.get('company.company')
        self.user = POOL.get('res.user')
        self.party = POOL.get('party.party')
        self.party_address = POOL.get('party.address')
        self.fiscalyear = POOL.get('account.fiscalyear')
        self.move = POOL.get('account.move')
        self.line = POOL.get('account.move.line')
        self.journal = POOL.get('account.journal')
        self.period = POOL.get('account.period')
        self.taxcode = POOL.get('account.tax.code')
        self.template = POOL.get('account.financial.statement.template')
        self.template_line = POOL.get(
            'account.financial.statement.template.line')
        self.report = POOL.get('account.financial.statement.report')
        self.report_line = POOL.get('account.financial.statement.report.line')

    def test0005views(self):
        '''
        Test views.
        '''
        test_view('account_financial_statement_analytic')

    def test0006depends(self):
        '''
        Test depends.
        '''
        test_depends()

    def create_moves(self):
        fiscalyear, = self.fiscalyear.search([])
        period = fiscalyear.periods[0]
        last_period = fiscalyear.periods[-1]
        journal_revenue, = self.journal.search([
                ('code', '=', 'REV'),
                ])
        journal_expense, = self.journal.search([
                ('code', '=', 'EXP'),
                ])
        revenue, = self.account.search([
                ('kind', '=', 'revenue'),
                ])
        self.account.write([revenue], {'code': '7'})
        receivable, = self.account.search([
                ('kind', '=', 'receivable'),
                ])
        self.account.write([receivable], {'code': '43'})
        expense, = self.account.search([
                ('kind', '=', 'expense'),
                ])
        self.account.write([expense], {'code': '6'})
        payable, = self.account.search([
                ('kind', '=', 'payable'),
                ])
        self.account.write([payable], {'code': '41'})
        chart, = self.account.search([
                ('parent', '=', None),
                ], limit=1)
        self.account.create([{
                    'name': 'View',
                    'code': '1',
                    'kind': 'view',
                    'parent': chart.id,
                    }])
        #Create some parties
        customer1, customer2, supplier1, supplier2 = self.party.create([{
                        'name': 'customer1',
                    }, {
                        'name': 'customer2',
                    }, {
                        'name': 'supplier1',
                    }, {
                        'name': 'supplier2',
                    }])
        self.party_address.create([{
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
        moves = self.move.create(vlist)
        self.move.post(moves)

    def test0010_with_analytic(self):
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.create_moves()
            template, = self.template.create([{
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
            root, = self.analytic_account.create([{
                        'type': 'root',
                        'name': 'Root',
                        }])
            analytic_account, = self.analytic_account.create([{
                        'type': 'normal',
                        'name': 'Analytic Account',
                        'parent': root.id,
                        'root': root.id,
                        }])
            fiscalyear, = self.fiscalyear.search([])
            period = fiscalyear.periods[0]

            report, = self.report.create([{
                        'name': 'Test report',
                        'template': template.id,
                        'current_fiscalyear': fiscalyear,
                        }])
            self.assertEqual(report.state, 'draft')
            self.report.calculate([report])
            self.assertEqual(report.state, 'calculated')

            results = {
                '01': Decimal('-130.0'),
                '02': Decimal('600.0'),
                }
            for line in report.lines:
                self.assertEqual(results[line.code], line.current_value)
                self.assertEqual(Decimal('0.0'), line.previous_value)
            self.report.draft([report])
            report.analytic_account = analytic_account
            report.save()
            self.report.calculate([report])
            for line in report.lines:
                self.assertEqual(Decimal('0.0'), line.current_value)
                self.assertEqual(Decimal('0.0'), line.previous_value)

            #Create analytic moves and test their value
            journal_revenue, = self.journal.search([
                    ('code', '=', 'REV'),
                    ])
            journal_expense, = self.journal.search([
                    ('code', '=', 'EXP'),
                    ])
            revenue, = self.account.search([
                    ('kind', '=', 'revenue'),
                    ])
            receivable, = self.account.search([
                    ('kind', '=', 'receivable'),
                    ])
            expense, = self.account.search([
                    ('kind', '=', 'expense'),
                    ])
            payable, = self.account.search([
                    ('kind', '=', 'payable'),
                    ])
            first_account_line = {
                'account': revenue.id,
                'credit': Decimal(100),
                'analytic_lines': [
                    ('create', [{
                                'account': analytic_account.id,
                                'name': 'Analytic Line',
                                'credit': Decimal(100),
                                'debit': Decimal(0),
                                'journal': journal_revenue.id,
                                'date': period.start_date,
                                }])
                    ]}
            second_account_line = {
                'account': expense.id,
                'debit': Decimal(30),
                'analytic_lines': [
                    ('create', [{
                                'account': analytic_account.id,
                                'name': 'Analytic Line',
                                'debit': Decimal(30),
                                'credit': Decimal(0),
                                'journal': journal_expense.id,
                                'date': period.start_date,
                                }])
                    ]}
            # Create some moves
            customer1, = self.party.search([
                    ('name', '=', 'customer1'),
                    ])
            supplier1, = self.party.search([
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
            self.move.create(vlist)
            self.report.draft([report])
            self.report.calculate([report])
            results = {
                '01': Decimal('-30.0'),
                '02': Decimal('100.0'),
                }
            for line in report.lines:
                self.assertEqual(results[line.code], line.current_value)
                self.assertEqual(Decimal('0.0'), line.previous_value)
            self.report.draft([report])
            report.analytic_account = root
            report.save()
            self.report.calculate([report])
            for line in report.lines:
                self.assertEqual(results[line.code], line.current_value)
                self.assertEqual(Decimal('0.0'), line.previous_value)

    def test0020_without_analytic(self):
        with Transaction().start(DB_NAME, USER, context=CONTEXT):
            self.create_moves()
            template, = self.template.create([{
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
            #This must be created manually otherwise template is not set.
            self.template_line.create([{
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
            fiscalyear, = self.fiscalyear.search([])
            period = fiscalyear.periods[0]

            report, = self.report.create([{
                        'name': 'Test report',
                        'template': template.id,
                        'current_fiscalyear': fiscalyear,
                        }])
            self.assertEqual(report.state, 'draft')
            self.report.calculate([report])
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
    from trytond.modules.account_financial_statement.tests import \
        test_account_financial_statement
    for test in test_account_financial_statement.suite():
        if test not in suite:
            suite.addTest(test)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestCase))
    return suite
