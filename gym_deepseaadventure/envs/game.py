# -*- coding:utf-8 -*-
import collections
import copy
import itertools
import random

import numpy as np


class Game(object):
    num_round = 3
    num_divers = 2
    max_air = 25

    def __init__(self):
        self.current_round = 1
        self.diver_index = 0
        self.air = Game.max_air
        self.tips = Tips()
        self.divers = [Diver(id) for id in range(Game.num_divers)]

    @staticmethod
    def throw_dice():
        return sum([random.randint(1, 3) for _ in range(2)])

    def render(self):
        print("-" * 100)
        print("Round{0}".format(self.current_round))
        print("Score")
        for diver in self.divers:
            print("  Diver{0}: {1}".format(diver.id, diver.compute_score()))
        print("Air: {0}".format(self.air))
        print("ship")
        for diver in self.divers:
            if diver.depth == 0:
                print("  {0} {1}".format(diver.id, ",".join([tip.mark() for tip in diver.current_tips])))
        print("sea")
        for depth in range(1, len(self.tips.tips) + 1):
            tip = self.tips.tips[depth - 1]
            mark = tip.mark()
            diver = [d for d in self.divers if d.depth == depth]
            if len(diver) == 1:
                direction_mark = "V" if diver[0].direction == 1 else "A"
                print("{0:2} {1} {2}{3} {4}".format(
                    depth, mark, direction_mark, diver[0].id, ",".join([tip.mark() for tip in diver[0].current_tips])))
            else:
                print("{0:2} {1}".format(depth, mark))
        if len(self.tips.carry_over) > 0:
            mark = "".join(tip.mark() for tip in self.tips.carry_over)
            diver = [d for d in self.divers if d.depth == len(self.tips.tips) + 1]
            if len(diver) == 1:
                direction_mark = "V" if diver[0].direction == 1 else "A"
                print("{0:2} {1} {2}{3} {4}".format(
                    len(self.tips.tips) + 1, mark, direction_mark, diver[0].id, ",".join([tip.mark() for tip in diver[0].current_tips])))
            else:
                print("{0:2} {1}".format(len(self.tips.tips) + 1, mark))
        print("-" * 100)

    def start(self):
        for current_round in range(1, Game.num_round + 1):
            self.current_round = current_round

            self.render()

            self.diver_index = -1
            while self.air >= 0 and any(not diver.return_ship for diver in self.divers):
                self.diver_index = (self.diver_index + 1) % len(self.divers)
                diver = self.divers[self.diver_index]

                if diver.return_ship:
                    continue

                self.air = max(-1, self.air - len(diver.current_tips))
                if self.air == -1:
                    break

                if diver.direction == 1 and diver.depth >= 1:
                    start_surface = yield ("ask surface", self)
                    if start_surface:
                        diver.direction = -1
                        print("Diver{0} decides surface".format(diver.id))

                        self.render()

                dice = Game.throw_dice()
                actual = max(0, dice - len(diver.current_tips))
                print("Diver{0}, Dice {1}, actual {2}".format(diver.id, dice, actual))

                before_depth = diver.depth
                for _ in range(actual):
                    diver.depth += diver.direction
                    while any([d.depth == diver.depth for d in self.divers if d.id != diver.id and d.depth > 0]):
                        diver.depth += diver.direction
                diver.depth = min(self.tips.max_depth, max(0, diver.depth))
                if diver.direction == 1:
                    while any([d.depth == diver.depth for d in self.divers if d.id != diver.id and d.depth > 0]):
                        diver.depth -= diver.direction
                    assert diver.depth >= before_depth

                self.render()

                if diver.depth == 0:
                    print("Success to return Diver{0}".format(diver.id))
                    diver.return_ship = True
                    continue

                if diver.depth <= len(self.tips.tips) and self.tips.tips[diver.depth - 1].is_blank() and len(diver.current_tips) > 0:
                    release_tip = yield ("ask release", self)
                    if release_tip is not None:
                        self.tips.release_at(diver.depth, release_tip)
                        print("Diver{0} release Tip {1} at {2}".format(diver.id, release_tip.mark(), diver.depth))

                        self.render()

                elif (diver.depth <= len(self.tips.tips) and not self.tips.tips[diver.depth - 1].is_blank() or
                      diver.depth == len(self.tips.tips) + 1 and len(self.tips.carry_over) > 0):
                    answer_get_tip = yield ("ask get", self)
                    if answer_get_tip:
                        get_tips = self.tips.get_at(diver.depth)
                        diver.current_tips += get_tips
                        print("Diver{0} get Tips {1} at {2}".format(
                            diver.id, ",".join([tip.mark() for tip in get_tips]), diver.depth))

                        self.render()
            print("Round{0} finish".format(current_round))

            self.air = Game.max_air
            new_carry_over = []
            for diver in self.divers:
                if not diver.return_ship:
                    new_carry_over += diver.current_tips
                    diver.current_tips = []
                diver.setup_round()
            self.tips.setup_round(new_carry_over)
        self.render()


class Diver(object):
    def __init__(self, id):
        self.id = id
        self.depth = 0
        self.direction = 1
        self.fixed_tips = []
        self.current_tips = []
        self.return_ship = False

    def setup_round(self):
        self.depth = 0
        self.direction = 1
        self.fixed_tips += self.current_tips
        self.current_tips = []
        self.return_ship = False

    def compute_score(self):
        return sum(tip.score for tip in self.fixed_tips)

    def current_tips_vector(self):
        counter = collections.Counter()
        for tip in self.current_tips:
            counter[tip.level] += 1
        return [counter[1], counter[2], counter[3], counter[4]]

    def fixed_tips_vector(self):
        counter = collections.Counter()
        for tip in self.fixed_tips:
            counter[tip.score] += 1
        ret = []
        for i in range(0, 16):
            ret.append(counter[i])
        return ret

class Tip(object):
    NULL = -1
    BLANK = 0
    LEVEL1 = 1
    LEVEL2 = 2
    LEVEL3 = 3
    LEVEL4 = 4

    def __init__(self, id, level, score):
        self.id = id
        self.level = level
        self.score = score

    def is_blank(self):
        return False

    def mark(self):
        return "[{0}]".format(self.level)


class BlankTip(object):
    def __init__(self):
        self.level = Tip.BLANK

    def is_blank(self):
        return True

    def mark(self):
        return "[X]"


class Tips(object):
    num_tips = 2 * 16
    max_score = sum(range(16)) * 2
    num_tips_each_level = 8
    num_levels = 4
    num_same_tips = 2
    num_variation = 16

    def __init__(self):
        original_tips = [
            [Tip(0, Tip.LEVEL1, 0), Tip(1, Tip.LEVEL1, 0), Tip(2, Tip.LEVEL1, 1), Tip(3, Tip.LEVEL1, 1), Tip(4, Tip.LEVEL1, 2), Tip(5, Tip.LEVEL1, 2), Tip(6, Tip.LEVEL1, 3), Tip(7, Tip.LEVEL1, 3)],
            [Tip(8, Tip.LEVEL2, 4), Tip(9, Tip.LEVEL2, 4), Tip(10, Tip.LEVEL2, 5), Tip(11, Tip.LEVEL2, 5), Tip(12, Tip.LEVEL2, 6), Tip(13, Tip.LEVEL2, 6), Tip(14, Tip.LEVEL2, 7), Tip(15, Tip.LEVEL2, 7)],
            [Tip(16, Tip.LEVEL3, 8), Tip(17, Tip.LEVEL3, 8), Tip(18, Tip.LEVEL3, 9), Tip(19, Tip.LEVEL3, 9), Tip(20, Tip.LEVEL3, 10), Tip(21, Tip.LEVEL3, 10), Tip(22, Tip.LEVEL3, 11), Tip(23, Tip.LEVEL3, 11)],
            [Tip(24, Tip.LEVEL4, 12), Tip(25, Tip.LEVEL4, 12), Tip(26, Tip.LEVEL4, 13), Tip(27, Tip.LEVEL4, 13), Tip(28, Tip.LEVEL4, 14), Tip(29, Tip.LEVEL4, 14), Tip(30, Tip.LEVEL4, 15), Tip(31, Tip.LEVEL4, 15)]
        ]

        data = copy.deepcopy(original_tips)
        for i in range(len(data)):
            random.shuffle(data[i])
        self.tips = list(itertools.chain(*data))
        self.carry_over = []

    def max_depth(self):
        return len(self.tips) + min(1, len(self.carry_over))

    def get_at(self, depth):
        if len(self.carry_over) > 0 and depth == len(self.tips) + 1:
            # carry over
            temp = self.carry_over
            self.carry_over = []
            return temp
        tip = self.tips[depth - 1]
        self.tips[depth - 1] = BlankTip()
        return [tip]

    def release_at(self, depth, tip):
        self.tips[depth - 1] = tip

    def setup_round(self, new_carry_over):
        self.tips = [tip for tip in self.tips if not tip.is_blank()]
        self.carry_over += new_carry_over

    def tips_vector(self):
        ret = [tip.level for tip in self.tips]
        ret += [Tip.NULL] * (Tips.num_tips - len(ret))
        return ret

    def carry_over_vector(self):
        counter = collections.Counter()
        for tip in self.carry_over:
            counter[tip.level] += 1
        return [counter[1], counter[2], counter[3], counter[4]]


def test():
    game = Game()
    g = game.start()
    ask, state = g.next()
    while True:
        try:
            if ask == "ask surface":
                diver = state.divers[state.diver_index]
                ask, state = g.send(diver.depth > 10)
            elif ask == "ask get":
                diver = state.divers[state.diver_index]
                if diver.id == 1:
                    if diver.direction == 1:
                        if diver.depth > 10:
                            ask, state = g.send(True)
                        else:
                            ask, state = g.send(False)
                    else:
                        one_turn_air = sum(len(d.current_tips) for d in state.divers) + 1
                        speed = sum([max(0, sum(random.randint(1, 3) for _ in range(2)) - (len(diver.current_tips) + 1)) for _ in range(1000)]) / 1000.0
                        need_turn = diver.depth / speed + 1
                        if state.air > one_turn_air * need_turn:
                            ask, state = g.send(True)
                        else:
                            ask, state = g.send(False)
                else:
                    if diver.direction == -1:
                        ask, state = g.send(True)
                    else:
                        ask, state = g.send(diver.depth > 10)

            elif ask == "ask release":
                diver = state.divers[state.diver_index]
                if len(diver.current_tips) > 0:
                    # release_tip = diver.current_tips.pop()
                    # ask, state = g.send(release_tip)
                    ask, state = g.send(None)
                else:
                    ask, state = g.send(None)
        except StopIteration:
            break


if __name__ == '__main__':
    test()
