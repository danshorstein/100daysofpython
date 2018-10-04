import random

import pandas as pd

def main():
    print_header()

    table = pd.read_html('https://github.com/talkpython/100daysofcode-with-python-course/blob/master/days/13-15-text-games/data/battle-table.csv')
    table = table[0].iloc[1:,:]
    table.index = table['Attacker']
    
    rolls_names = list(table.index)

    rolls = [Roll(roll, table) for roll in rolls_names]

    name = get_players_name()

    player1 = Player(name)
    player2 = Player("computer")

    game_loop(player1, player2, rolls, table)

class Roll:
    def __init__(self, roll, table):
        self.roll = roll
        self.table = table
        self.rolls_names = list(self.table['Attacker'])
        if self.roll in self.rolls_names:
            self.roll_wins = self.get_roll_wins()
            self.roll_loses = self.get_roll_loses()
        else:
            print(f'{roll} is not an option! try again: ')
            self.roll = None

    def get_roll_wins(self):
        return list(self.table.loc[self.roll,:][self.table.loc[self.roll,:] == 'win'].index)

    def get_roll_loses(self):
        return list(self.table.loc[self.roll,:][self.table.loc[self.roll,:] == 'lose'].index)

    def can_defeat(self, other_roll):
        if other_roll.roll in self.roll_wins:
            return "WIN!"
        elif other_roll.roll in self.roll_loses:
            return "LOSE!"
        else:
            return "TIE!"

class Player:
    def __init__(self, name):
        self.name = name

def print_header():
    print('---------------------')
    print('-rock scissors paper-')
    print('---------------------')

def get_players_name():
    return input('what\'s yer name? ')

def game_loop(player1, player2, rolls, table):
    count = 1
    score = {player1: 0, player2: 0}

    while count <= 3:
        p2_roll = random.choice(rolls)
        
        while True:
            p1_roll = Roll(input(f'Choose a roll ({', '.join(list(table.index))}): '), table)
            if p1_roll.roll:
                break

        outcome = p1_roll.can_defeat(p2_roll)
        
        # display throws
        print(f'{player1.name} threw {p1_roll.roll}. {player2.name} threw {p2_roll.roll}.')

        if outcome == 'WIN!':
            print(f'{player1.name} wins this round!')
            score[player1] += 1

        elif outcome == 'LOSE!':
            print(f'{player2.name} wins this round!')
            score[player2] += 1

        elif outcome == 'TIE!':
            print('It was a tie!!!')
        
        print()

        count += 1
    print(f'Overall winner is {max(score, key=lambda x: score[x]).name}')

if __name__ == '__main__':
    main()