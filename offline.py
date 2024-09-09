from server import *
import random, traceback
random.seed(0)
gamer = Gamer(0, False)

DEBUG = False

p1 = Player('p1')
p2 = Player('p2')
p3 = Player('p3')
p4 = Player('p4')

p1.offline()
p2.offline()
p3.offline()
p4.offline()

p1.set_gamer(gamer)
p2.set_gamer(gamer)

p1.ready_for_game()
p2.ready_for_game()

print(p1.name, ':', p1.get_pokes())
p1.choose_pokes_side(
    True if bool(int(input('reverse?(bool, 0 for first one, 1 for second):'))) else False
)
print(p2.name, ':', p2.get_pokes())
p2.choose_pokes_side(
    True if bool(int(input('reverse?(bool, 0 for first one, 1 for second):'))) else False
)

while 1:
    while 1:
        try:
            print("\n\033[92mTable ===>", gamer.displayed_pokes.json(), f'\033[0m\n{p1.name}:', end='')
            print(p1.get_pokes())
            c = input('[y, 1]play cards [n, 0]draw cards\n')
            if c in ['y', '1']:
                p1.show(
                    p1.choose_pokes_index(int(input('begin index(int, start from 0):')), int(input('end index(int, not included):')))
                )
            elif c in ['n', '0']:
                p1.scout(
                    bool(int(input('index(bool, 0 for last, 1 for fist):'))),
                    bool(int(input('reverse(bool, 0 for origin, 1 for reversed):'))),
                    int(input('insert to(int, position in your pokes):'))
                )
            else:
                raise ValueError(f'Invalid input {c}')
        except Exception as e:
            if DEBUG:
                traceback.print_exc()
            print(f"\n\033[91m{e}\033[0m")
        else:
            break
    while 1:
        try:
            print("\n\033[92mTable ===>", gamer.displayed_pokes.json(), f'\033[0m\n{p2.name}:', end='')
            print(p2.get_pokes())
            c = input('[y, 1]play cards [n, 0]draw cards\n')
            if c in ['y', '1']:
                p2.show(
                    p2.choose_pokes_index(int(input('begin index(int, start from 0):')), int(input('end index(int, not included):')))
                )
            elif c in ['n', '0']:
                p2.scout(
                    bool(int(input('index(bool, 0 for last, 1 for fist):'))),
                    bool(int(input('reverse(bool, 0 for origin, 1 for reversed):'))),
                    int(input('insert to(int, position in your pokes):'))
                )
            else:
                raise ValueError(f'Invalid input {c}')
        except Exception as e:
            if DEBUG:
                traceback.print_exc()
            print(f"\n\033[91m{e}\033[0m")
        else:
            break