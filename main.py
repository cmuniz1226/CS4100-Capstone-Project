from pypokerengine.api.game import setup_config, start_poker
from examples.players.honest_player import HonestPlayer
from examples.players.fish_player import FishPlayer
from examples.players.random_player import RandomPlayer
from examples.players.mcts_player import MCTSPlayer
from examples.players.emulator_player import EmulatorPlayer

NUM_OTHER_PLAYERS = 2
config = setup_config(max_round=10, initial_stack=500, small_blind_amount=5)
our_player = MCTSPlayer()
our_player.set_opponents_model(RandomPlayer())

other_players = [RandomPlayer() for _ in range(NUM_OTHER_PLAYERS)]

for player in other_players:
    if isinstance(player, EmulatorPlayer):
        player.set_opponents_model(RandomPlayer())

config.register_player(name="Chris and Jackson", algorithm=our_player)
player_number = 2
for player in other_players:
    p_name = "Player" + str(player_number)
    config.register_player(name=p_name, algorithm=player)
    player_number += 1
    
game_result = start_poker(config, verbose=1)
