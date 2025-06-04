# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import PoolMeta


class AnalyticAccount(metaclass=PoolMeta):
    __name__ = 'analytic_account.account'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.currency.searcher='search_currency'

    @classmethod
    def search_currency(cls, name, clause):
        nested = clause[0][len(name) + 1:]
        return [('company.currency' + nested, *clause[1:])]


