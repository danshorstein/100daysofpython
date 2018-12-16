from collections import defaultdict

class FSLineItem:
    def __init__(self, account_name, balance, normal_balance, fs_line_item):
        self.account_name = account_name
        self.balance = balance
        self.normal_balance = normal_balance
        self.fs_line_item = fs_line_item
        
    def debit(self, amount):
        self.balance += amount

    def credit(self, amount):
        self.balance -= amount

    def __repr__(self):
        return f'''
        -----------------------------
        Account: {self.account_name}
        Type: {self.__name__}
        Balance: {self.balance}
        FS Line Item: {self.fs_line_item}'''


class TrialBalance:
    # Holds the balances of all accounts
    def __init__(self):
        self.trial_balance = defaultdict(list)

    def __repr__(self):
        for act, bal in self.trial_balance.items:
            return(f'Account {act} has a balance of {bal}')

class Asset(FSLineItem):
    def __init__(self, account_name, balance=0, normal_balance='Debit', fs_line_item='Total Assets', tangible=True):
        super().__init__(account_name, balance, normal_balance, fs_line_item)
        self.tangible = tangible
        self.__name__ = 'Asset'


class Liability(FSLineItem):
    def __init__(self, account_name, balance=0, normal_balance='Credit', fs_line_item='Liability'):
        super().__init__(account_name, balance, normal_balance, fs_line_item)
        self.__name__ = 'Liability'


class Equity(FSLineItem):
    def __init__(self, account_name, balance=0, normal_balance='Credit', fs_line_item='Equity'):
        super().__init__(account_name, balance, normal_balance, fs_line_item)
        self.__name__ = 'Equity'


class Transaction:
    def __init__(self, accounts='', amounts=''):
        self.accounts = list(accounts)
        self.amounts = list(amounts)
        self.trial_balance = TrialBalance()
    
    def add_line(self, account, amount):
        self.accounts.append(account)
        self.amounts.append(amount)

    def enter(self):
        if round(sum(self.amounts), 0) == 0:

            for act, amt in zip(self.accounts, self.amounts):
                if amt > 0:
                    act.debit(amt)
                else:
                    act.credit(amt * -1)
            self.trial_balance[act] += amt   

        else:
            print('make sure your debits = credits!!!')

    
# class Cash(Asset):
#     def __init__(self, normal_balance, fs_line_item, tangible, )

if __name__ == '__main__':
    # Initiate accounts
    cash = Asset('Cash')
    inventory = Asset('Inventory')
    accounts_receivable = Asset('Accounts Receivable')
    accounts_payable = Liability('Accounts Payable')
    equity = Equity('Equity')
    
    # Book an entry
    entry = Transaction()
    entry.add_line(cash, 10000)
    entry.add_line(accounts_payable, -2000)
    entry.add_line(equity, -8000)
    entry.enter()

    print(TrialBalance())