define e = Character("Eileen")
define a = Character("Alice")
init python:
    class Girl(object):
        def __init__(self, name, love):
            self.name = name
            self.love = love
default anna = Girl("Anna", 7)
default money = 120
default alice_love = 3
default alice_trust = 1
default met_alice = False
default hp = 50
default day = 1
default inv = {"apple": 2, "sword": 1}
default flags = [True, False]
default name_p = "Hero"
default loop_i = 0

label main_menu:
    return

label start:
    e "Hello there. You have [money] coins."
    $ met_alice = True
    a "Hi!"
    menu:
        "Be nice":
            $ alice_love += 1
            $ anna.love += 2
        "Be rude":
            $ alice_love -= 1
        "Secret" if alice_love >= 5:
            jump alice_date
        "Buy a gift" if money > 100:
            $ money -= 50
            $ alice_trust += 1
    if alice_trust >= 3 and met_alice:
        jump alice_date
    $ day += 1
    e "End."
    return

label alice_date:
    a "A date!"
    $ hp -= 5
    return
