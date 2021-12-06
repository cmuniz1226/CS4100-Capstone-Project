import json, re
from os import listdir, mkdir
from os.path import isfile, join, exists

INITIAL_STACK = 200
BOT_NAME = 'Stonks'

DECODER_DATA_IND = 0
DECODER_SEEK_IND = 1

GAMEPLAY_DATA_FILE_PATH = '../gameplay_data'
CSV_FILE_PATH = GAMEPLAY_DATA_FILE_PATH + '/CSVs/'


def get_average_profit(file_name, bot_name, initial_stack):
    """
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


def write_to_CSV(initial_stack, bot_name, csv_file_name, player_type='[a-zA-Z]+', round_count='[0-9]+', other_player_count='[0-9]+', playouts_count='[0-9]+'):
    
    if not exists(CSV_FILE_PATH):
        mkdir(CSV_FILE_PATH)

    file_name_pattern = r'{0}_{1}-rounds_{2}-others_{3}-playouts.json'.format(player_type, round_count, 
        other_player_count, playouts_count)
    inlcude_new_line =  False

    for file_name in listdir(GAMEPLAY_DATA_FILE_PATH):
        should_get_data = bool(re.match(file_name_pattern, file_name))
        if should_get_data:
            file_path = join(GAMEPLAY_DATA_FILE_PATH, file_name)
            avg_profit = get_average_profit(file_path, bot_name, initial_stack)
            csv_file = open(CSV_FILE_PATH + csv_file_name, 'a')
            if inlcude_new_line:
                csv_file.write('\n')
            else:
                inlcude_new_line = True
            csv_file.write('{0},'.format(avg_profit))
            csv_file.close()


def number_of_rounds():
    metrics = [5, 10, 15, 20]
    for metric in metrics:
        write_to_CSV(INITIAL_STACK, BOT_NAME, 'random_average_profit_{0}_rounds.csv'.format(metric), player_type='RandomPlayer', 
            round_count=metric, other_player_count=3, playouts_count=10000)
        write_to_CSV(INITIAL_STACK, BOT_NAME, 'honest_average_profit_{0}_rounds.csv'.format(metric), player_type='HonestPlayer', 
            round_count=metric, other_player_count=3, playouts_count=10000)


def number_of_playouts():
    metrics = [100, 1000, 10000, 100000]
    for metric in metrics:
        write_to_CSV(INITIAL_STACK, BOT_NAME, 'random_average_profit_{0}_playouts.csv'.format(metric), player_type='RandomPlayer', 
            round_count=10, other_player_count=3, playouts_count=metric)
        write_to_CSV(INITIAL_STACK, BOT_NAME, 'honest_average_profit_{0}_playouts.csv'.format(metric), player_type='HonestPlayer', 
            round_count=10, other_player_count=3, playouts_count=metric)

def number_of_other_players():
    metrics = [1, 3, 5, 7]
    for metric in metrics:
        write_to_CSV(INITIAL_STACK, BOT_NAME, 'random_average_profit_{0}_other_players.csv'.format(metric), player_type='RandomPlayer', 
            round_count=10, other_player_count=metric, playouts_count=10000)
        write_to_CSV(INITIAL_STACK, BOT_NAME, 'honest_average_profit_{0}_other_players.csv'.format(metric), player_type='HonestPlayer', 
            round_count=10, other_player_count=metric, playouts_count=10000)

def main():
    number_of_rounds()
    number_of_playouts()
    number_of_other_players()
    write_to_CSV(INITIAL_STACK, BOT_NAME, 'random_average_profit_all_metrics.csv', player_type='RandomPlayer')
    write_to_CSV(INITIAL_STACK, BOT_NAME, 'honest_average_profit_all_metrics.csv', player_type='HonestPlayer')


if __name__ == "__main__":
    main()