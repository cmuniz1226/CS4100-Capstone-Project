import json, re
from os import listdir, mkdir
from os.path import join, exists
import os
import inspect
import csv
import sys
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir) 
from result_params import HEURISTICS, OPPONENT_ALGORITHMS, NUM_ROUNDS, \
    NUM_OTHER_PLAYERS, NUM_PLAYOUTS

INITIAL_STACK = 200
BOT_NAME = 'Stonks'

DECODER_DATA_IND = 0
DECODER_SEEK_IND = 1

GAMEPLAY_DATA_FILE_PATH = './gameplay_data'
CSV_FILE_PATH = GAMEPLAY_DATA_FILE_PATH + '/CSVs/'


def get_average_profit(file_name, bot_name, initial_stack):
    """
    Given the name for a game results JSON file, the name of our bot, and 
    the initial stack the bot started out with in each game, return the average
    profit of that bot.
    """
    gameplay_data_file = open(file_name, 'r')
    game_results = gameplay_data_file.read()
    gameplay_data_file.close()


    results = game_results.split('}')
    results = results[: len(results) - 1]
    result_dicts = []
    for result in results:
        result += '}'
        result_dicts.append(json.loads(result))
    final_stacks = 0
    num_results = len(result_dicts)
    for dict in result_dicts:
        final_stacks += dict[bot_name]

    return (final_stacks / num_results) - initial_stack


# Result File Name Format: <heuristic_function>_<other-player-algo>_<num-rounds>_<num-other-players>_<num-playouts>
def write_avg_profit_data_to_CSV(bot_name, initial_stack, csv_file_name, heuristic_function='[a-zA-Z]+', opponent_algo='[a-zA-Z]+', round_count='[0-9]+',
    other_player_count='[0-9]+', playouts_count='[0-9]+'):
    """
    Given the name of a bot, the bot's initial stack, and the CSV file name to write to, 
    gather average profit data based on specified regex patterns for metrics that apply
    to previously generated JSON game results.
    """
    if not exists(CSV_FILE_PATH):
        mkdir(CSV_FILE_PATH)

    # Get all files matching criteria
    # Get average profit
    # Write All profit computations to CSV
    csv_file = open(CSV_FILE_PATH + csv_file_name, 'w', newline='')
    writer = csv.writer(csv_file)
    
    file_name_pattern = r'{0}_{1}_{2}-rounds_{3}-others_{4}-playouts.json'.format(heuristic_function, opponent_algo, 
        round_count, other_player_count, playouts_count)
    
    for file_name in listdir(GAMEPLAY_DATA_FILE_PATH):
        should_get_data = bool(re.match(file_name_pattern, file_name))
        if should_get_data:
            file_path = join(GAMEPLAY_DATA_FILE_PATH, file_name)
            avg_profit = get_average_profit(file_path, bot_name, initial_stack)
            writer.writerow([avg_profit])
    
    csv_file.close()

def number_of_rounds():
    for heuristic in HEURISTICS:
        for opp_algorithm in OPPONENT_ALGORITHMS:
            for rounds in NUM_ROUNDS:
                write_avg_profit_data_to_CSV(BOT_NAME, INITIAL_STACK, '{0}_{1}_average_profit_{2}_rounds.csv'.format(heuristic.__name__, opp_algorithm.__name__, rounds), 
                    heuristic_function=heuristic.__name__, opponent_algo=opp_algorithm.__name__, round_count=rounds, other_player_count=3, playouts_count=10000)

def number_of_other_players():
    for heuristic in HEURISTICS:
        for opp_algorithm in OPPONENT_ALGORITHMS:
            for others in NUM_OTHER_PLAYERS:
                write_avg_profit_data_to_CSV(BOT_NAME, INITIAL_STACK, '{0}_{1}_average_profit_{2}_others.csv'.format(heuristic.__name__, opp_algorithm.__name__, others), 
                    heuristic_function=heuristic.__name__, opponent_algo=opp_algorithm.__name__, round_count=10, other_player_count=others, playouts_count=10000)

def number_of_playouts():
    for heuristic in HEURISTICS:
        for opp_algorithm in OPPONENT_ALGORITHMS:
            for playouts in NUM_PLAYOUTS:
                write_avg_profit_data_to_CSV(BOT_NAME, INITIAL_STACK, '{0}_{1}_average_profit_{2}_playouts.csv'.format(heuristic.__name__, opp_algorithm.__name__, playouts), 
                    heuristic_function=heuristic.__name__, opponent_algo=opp_algorithm.__name__, round_count=10, other_player_count=3, playouts_count=playouts)
            

if __name__ == "__main__":
    number_of_rounds()
    number_of_playouts()
    number_of_other_players()
    for heuristic in HEURISTICS:
        for opp_algo in OPPONENT_ALGORITHMS:
            write_avg_profit_data_to_CSV(BOT_NAME, INITIAL_STACK, '{0}_{1}_average_profit_all_metrics.csv'.format(heuristic.__name__, opp_algo.__name__), 
            heuristic_function=heuristic.__name__, opponent_algo=opp_algo.__name__)