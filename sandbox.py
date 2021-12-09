import json
from random import Random
from pypokerengine.api.game import setup_config, start_poker
from examples.players.honest_player import HonestPlayer
from examples.players.random_player import RandomPlayer
from examples.players.mcts_player import MCTSPlayer
from examples.players.emulator_player import EmulatorPlayer

#NUM_OTHER_PLAYERS = 2
# MAX_ROUNDS = 20
INITIAL_STACK = 200
SMALL_BLIND = 5


RESULTS_DIR = './gameplay_data/'
NUM_GAMES = 10


def play_game_with_settings(max_rounds, num_other_players, opponent_player, result_file, num_playouts):
    """
    Given the settings for the maximum number of rounds in a game, the number of other players, the
    type of other players, the file name to save results to, and the number of MCTS playouts to run,
    runs an instance of the MCTSPlayer against those other players and saves the game results to a given
    file path.
    """
    config = setup_config(max_round=max_rounds, initial_stack=INITIAL_STACK, small_blind_amount=SMALL_BLIND)
    our_player = MCTSPlayer(num_playouts)
    our_player.set_opponents_model(RandomPlayer())

    other_players = [opponent_player() for _ in range(num_other_players)]

    for player in other_players:
        if isinstance(player, EmulatorPlayer):
            player.set_opponents_model(RandomPlayer())

    config.register_player(name="Stonks", algorithm=our_player)
    player_number = 1
    for player in other_players:
        p_name = "Player" + str(player_number)
        config.register_player(name=p_name, algorithm=player)
        player_number += 1
        
    game_result = start_poker(config, verbose=1)
    result_data = {}
    for player in game_result["players"]:
        result_data[player["name"]] =  player['stack']

    if result_file is not None:
        result_file = open(result_file, 'a')
        result_file.write(json.dumps(result_data))
        result_file.close()

    print(result_data)

play_game_with_settings(10, 2, RandomPlayer, None, 10000)