import json
from pypokerengine.api.game import setup_config, start_poker
from examples.players.honest_player import HonestPlayer
from examples.players.random_player import RandomPlayer
from examples.players.mcts_player import MCTSPlayer, random_action, \
    nyu_heuristic_function, custom_heuristic
from examples.players.emulator_player import EmulatorPlayer
from threading import Thread
from multiprocessing import Process

INITIAL_STACK = 200
SMALL_BLIND = 5


RESULTS_DIR = './gameplay_data/'
NUM_GAMES = 30


def play_game_with_settings(max_rounds, num_other_players, opponent_player, result_file, num_playouts, heuristic_function):
    """
    Given the settings for the maximum number of rounds in a game, the number of other players, the
    type of other players, the file name to save results to, and the number of MCTS playouts to run,
    runs an instance of the MCTSPlayer against those other players and saves the game results to a given
    file path.
    """
    config = setup_config(max_round=max_rounds, initial_stack=INITIAL_STACK, small_blind_amount=SMALL_BLIND)
    our_player = MCTSPlayer(num_playouts, heuristic_function)
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

    result_file = open(result_file, 'a')
    result_file.write(json.dumps(result_data))
    result_file.close()

    print(result_data)

heuristics = [nyu_heuristic_function, custom_heuristic, random_action]
opponent_algorithms = [RandomPlayer, HonestPlayer, EmulatorPlayer]
num_rounds = [5, 10, 15, 20]
num_other_players = [1, 3, 5, 7]
num_playouts = [100, 1000, 10000, 100000]

def gather_data(heuristic_function):
    """
    Given a heuristic function, gather data on the average profit of all the games played 
    given certain game parameters (i.e., opponent algorithms, number of rounds, etc.).
    """
    # Result File Name Format: <heuristic_function>_<other-player-algo>_<num-rounds>_<num-other-players>_<num-playouts>
    threads = []
    for opp_algo in opponent_algorithms:
        threads.append(Thread(target=run_game_with_heuristic_and_opponent_models, args=(opp_algo, heuristic_function)))
    [thread.start() for thread in threads]
    [thread.join() for thread in threads]

def run_game_with_heuristic_and_opponent_models(opponent_algorithm, heuristic_function):
    """
    Given an opponent algorithm and a heuristic function, generate JSON data with the results of playing games
    (with different settings) with those guidelines.
    """
    if opponent_algorithm.__name__ == 'EmulatorPlayer':
        num_rounds_to_run = [5, 10]
    else:
        num_rounds_to_run = num_rounds
    for rounds in num_rounds_to_run:
        for other_players in num_other_players:
            for playouts in num_playouts:
                result_file_path = RESULTS_DIR + "{0}_{1}_{2}-rounds_{3}-others_{4}-playouts.json".format(heuristic_function.__name__, opponent_algorithm.__name__, rounds, other_players, playouts)
                for _ in range(NUM_GAMES):
                    play_game_with_settings(rounds, other_players, opponent_algorithm, result_file_path, playouts, heuristic_function)

if __name__ == '__main__':
    processes = []
    for heuristic in heuristics:
        processes.append(Process(target=gather_data, args=[heuristic]))
    [process.start() for process in processes]
    [process.join() for process in processes]