from examples.players.honest_player import HonestPlayer
from examples.players.random_player import RandomPlayer
from examples.players.mcts_player import MCTSPlayer, random_action, \
    nyu_heuristic_function, custom_heuristic
from examples.players.emulator_player import EmulatorPlayer


HEURISTICS = [nyu_heuristic_function, custom_heuristic, random_action]
OPPONENT_ALGORITHMS = [RandomPlayer, HonestPlayer, EmulatorPlayer]
NUM_ROUNDS = [5, 10, 15, 20]
NUM_OTHER_PLAYERS = [1, 3, 5, 7]
NUM_PLAYOUTS = [100, 1000, 10000, 100000]