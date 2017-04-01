# -*- coding:utf-8 -*-
import collections
import copy
import itertools
import logging
import random

import numpy as np
import gym
from gym import error, spaces, utils
from gym.utils import seeding

from game import Game, Tip, Tips, Diver


class Action(object):
    skip = 0
    do = 1

class DeepSeaAdventureEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    dtype = np.uint8

    def __init__(self):
        self.action_space = spaces.Discrete(2)  # skip, do
        # dimention = 87
        self.observation_space = spaces.MultiDiscrete(
            # round
            [[1, Game.num_round],
             # scene 0: ask surface, 1: ask get, 2: ask release
             [0, 2],
             # air
             [-1, Game.max_air]] +
            # diver depth
            [[0, Tips.num_tips] for _ in range(Game.num_divers)] +
            # diver direction
            [[0, 1] for _ in range(Game.num_divers)] +
            # diver current tips
            [[0, Tips.num_tips_each_level] for _ in range(Tips.num_levels * Game.num_divers)] +
            # diver fixed tips
            [[0, Tips.num_same_tips] for _ in range(Tips.num_variation * Game.num_divers)] +
            # diver score
            [[0, Tips.max_score] for _ in range(Game.num_divers)] +
            # diver return ship
            [[0, 1] for _ in range(Game.num_divers)] +
            # tips
            [[Tip.NULL, Tip.LEVEL4] for _ in range(Tips.num_tips)] +
            # carry over
            [[0, Tips.num_tips_each_level] for _ in range(Tips.num_levels)]
        )

    def convert_vector(self):
        if self.ask == 'ask surface':
            scene = 0
        elif self.ask == 'ask get':
            scene = 1
        elif self.ask == 'ask release':
            scene = 2
        return (
            [self.game.current_round,
             scene,
             self.game.air] +
            [diver.depth for diver in self.game.divers] +
            [diver.direction for diver in self.game.divers] +
            list(itertools.chain(*[diver.current_tips_vector() for diver in self.game.divers])) +
            list(itertools.chain(*[diver.fixed_tips_vector() for diver in self.game.divers])) +
            [diver.compute_score() for diver in self.game.divers] +
            [int(diver.return_ship) for diver in self.game.divers] +
            self.game.tips.tips_vector() +
            self.game.tips.carry_over_vector())

    def _step(self, action):
        assert self.game.diver_index == 0
        try:
            # player step
            if action == Action.skip:
                if self.ask == 'ask surface':
                    self.ask, self.state = self.g.send(False)
                elif self.ask == 'ask get':
                    self.ask, self.state = self.g.send(False)
                elif self.ask == 'ask release':
                    self.ask, self.state = self.g.send(None)
            elif action == Action.do:
                if self.ask == 'ask surface':
                    self.ask, self.state = self.g.send(True)
                elif self.ask == 'ask get':
                    self.ask, self.state = self.g.send(True)
                elif self.ask == 'ask release':
                    diver = self.game.divers[0]
                    release_tip = diver.current_tips.pop()
                    self.ask, self.state = self.g.send(release_tip)

            # opponent step
            while self.game.diver_index == 1:
                opponent = self.game.divers[1]
                if self.ask == 'ask surface':
                    self.ask, self.state = self.g.send(opponent.depth > 10)
                elif self.ask == 'ask get':
                    if opponent.direction == 1:
                        if opponent.depth > 10:
                            self.ask, self.state = self.g.send(True)
                        else:
                            self.ask, self.state = self.g.send(False)
                    else:
                        one_turn_air = sum(len(d.current_tips) for d in self.game.divers) + 1
                        speed = sum([max(0, sum(random.randint(1, 3) for _ in range(2)) - (len(opponent.current_tips) + 1)) for _ in range(1000)]) / 1000.0
                        need_turn = opponent.depth / speed + 1
                        if self.game.air > one_turn_air * need_turn:
                            self.ask, self.state = self.g.send(True)
                        else:
                            self.ask, self.state = self.g.send(False)
                elif self.ask == 'ask release':
                    self.ask, self.state = self.g.send(None)

        except StopIteration:
            player = self.game.divers[0]
            player_score = player.compute_score()
            opponent = self.game.divers[1]
            opponent_score = opponent.compute_score()
            if player_score > opponent_score:
                return self.convert_vector(), 1.0, True, {}
            else:
                return self.convert_vector(), -1.0, True, {}

        return self.convert_vector(), 0.0, False, {}

    def _reset(self):
        self.game = Game()
        self.g = self.game.start()
        self.ask, self.state = self.g.next()
        return self.convert_vector()

    def _render(self, mode='human', close=False):
        self.game.render()


if __name__ == '__main__':
    test()
