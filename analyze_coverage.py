import time
import util
import argparse
from chessgraph import Graph
import pathlib
import chess
from util import read_pgn_files_in_directory
from apiclient import LichessExplorerService
from datetime import datetime


def main():
    parser = argparse.ArgumentParser("Use lichess database to find most likely positions, "
                                     "explored and unexplored, "
                                     "given that we are using the moves from opening graph.")
    parser.add_argument("color", choices=["b", "w"], help="Choose 'b' for black or 'w' for white.")
    parser.add_argument("--database", choices=["lichess", "master"], default="lichess",
                        help="Use either database of masters games or larger database of lichess games")
    parser.add_argument('--starting_pos', type=str,
        help="Specify the starting position from where to search for positions as a string in fen format."
             "The move counters are not necessary, only the "
             "first part of the fen. e.g. 'rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2'."
             "The position has to be part of the opening tree."
    )
    parser.add_argument('--output_fen_only', action='store_true',
                        help='Flag to only put a list of FENs in the output without any other information')

    args = parser.parse_args()
    color = args.color
    database = args.database
    output_fen_only = args.output_fen_only
    if args.starting_pos is not None and len(args.starting_pos) > 0:
        starting_position = util.relevant_fen_part(args.starting_pos)
    else:
        starting_position = util.relevant_fen_part(chess.STARTING_FEN)

    if args.color == 'b':
        path = pathlib.Path("data/black")
    else:
        path = pathlib.Path("data/white")
    games_list = read_pgn_files_in_directory(path)
    graph = Graph(args.color, games_list)

    if not graph.node_exists(starting_position):
        print("The specified starting fen is not part of the opening tree.")
        return

    api_service = LichessExplorerService(database=database)
    position_probabilities = {}

    count_explored_positions = initialize_explored_positions(position_probabilities, graph, starting_position)

    populate_probability_data(position_probabilities, api_service, graph, starting_position, count_explored_positions)

    print(f"Number of positions with probabilities: {len(position_probabilities)}")

    now = datetime.now()
    datetime_string = "__" + now.strftime("%Y-%m-%d__%H_%M_%S")
    if args.starting_pos is not None and len(args.starting_pos) > 0:
        pos_string = "_" + "custom_starting_pos"
        starting_depth = get_depth_of_position(starting_position, graph)
        pos_string = pos_string + "_" + str(starting_depth)
    else:
        pos_string = ""
    filename = "probabilities_" + color + "_" + database + pos_string + datetime_string + ".txt"
    print_data(position_probabilities, filename, output_fen_only)


def get_depth_of_position(fen, graph):
    if fen == util.relevant_fen_part(chess.STARTING_FEN):
        return 0
    origin = graph.get_first_origin(fen)
    list_of_san_moves = util.build_list_of_san_moves_from_origin_string(origin)
    return len(list_of_san_moves)


def print_data(position_probabilities, filename, output_fen_only):
    with open(filename, "a") as file:
        sorted_position_probs = sorted(position_probabilities.items(), key=lambda x: x[1]['prob'], reverse=True)
        for i, keyValuePair in enumerate(sorted_position_probs, start=1):
            if output_fen_only:
                print(keyValuePair[0], file=file)
            else:
                print(f"{i}:", file=file)
                pretty_print_entry(keyValuePair[0], keyValuePair[1], file)
                print("", file=file)


def pretty_print_entry(fen, prob_entry, file):
    print(fen, file=file)
    print(f"Depth {prob_entry['depth']}", file=file)
    if prob_entry['color'] == 'w':
        color_to_print = 'WHITE'
    elif prob_entry['color'] == 'b':
        color_to_print = 'BLACK'
    else:
        raise Exception("Invalid color entry " + prob_entry['color'])
    if prob_entry['explored']:
        explored_marker = ''
    else:
        explored_marker = '(UNEXPLORED)'
    print(f"Color to move: {color_to_print} {explored_marker}", file=file)
    print(f"Probability: {prob_entry['prob']}", file=file)
    print("Origins:", file=file)
    for origin_string in prob_entry['origins']:
        print(origin_string, file=file)


def populate_probability_data(position_probabilities, apiService, graph, starting_pos, count_explored_positions):
    curr_idx = 0
    for curr_fen in graph.breadth_first(starting_pos):
        curr_idx += 1
        print(f"Processing position {curr_fen} which is the {curr_idx}th of {count_explored_positions} positions")
        curr_color = util.fen_to_color(curr_fen)
        if curr_color == graph.color:
            move_from_node = graph.get_moves(curr_fen)[0]
            next_fen = util.get_next_fen(curr_fen, move_from_node)
            position_probabilities[next_fen]['prob'] += position_probabilities[curr_fen]['prob']
        else:
            curr_list_of_uci = get_list_of_uci_moves(curr_fen, graph)
            time.sleep(1)  # respect rate limit (with sleep for only half a second, rate limit was exceeded)
            move_probs_list = apiService.get_move_probabilities(curr_list_of_uci)
            for move_prob in move_probs_list:
                next_fen = util.successor_fen(curr_fen, move_prob['uci'])
                if next_fen not in position_probabilities:
                    next_color = util.fen_to_color(next_fen)
                    position_probabilities[next_fen] = initialize_data_for_a_position(next_color, False)
                position_probabilities[next_fen]['prob'] += position_probabilities[curr_fen]['prob'] * move_prob['prob']
                if not graph.node_exists(next_fen):
                    add_origins_for_unexplored_position(curr_fen, next_fen, move_prob['uci'],
                                                        graph, position_probabilities)
                    position_probabilities[next_fen]['depth'] = position_probabilities[curr_fen]['depth'] + 1


def get_list_of_uci_moves(curr_fen, graph):
    if curr_fen == util.relevant_fen_part(chess.STARTING_FEN):
        return []
    first_origin = graph.get_first_origin(curr_fen)
    curr_list_of_uci = util.translate_origin_string_into_list_of_uci(first_origin)
    return curr_list_of_uci


def initialize_explored_positions(position_probabilities, graph, starting_position):
    count = 0
    for fen in graph.breadth_first(starting_position):
        count += 1
        position_probabilities[fen] = initialize_data_for_a_position(util.fen_to_color(fen), True)
        position_probabilities[fen]['origins'].extend(graph.get_origins(fen))
        position_probabilities[fen]['depth'] = get_depth_of_position(fen, graph)
    position_probabilities[starting_position]['prob'] = 1
    return count




def add_origins_for_unexplored_position(curr_fen, next_fen, uci_move, graph, position_probabilities):
    initial_board_position = util.relevant_fen_part(chess.STARTING_FEN)
    curr_origins = graph.get_origins(curr_fen)
    if len(curr_origins) == 0 and curr_fen == initial_board_position:
        curr_origins = [""]
    for origin in curr_origins:
        list_of_uci = util.translate_origin_string_into_list_of_uci(origin)
        list_of_uci.append(uci_move)
        new_origin = util.translate_list_of_uci_into_origin_string(list_of_uci)
        position_probabilities[next_fen]['origins'].append(new_origin)


def initialize_data_for_a_position(color, explored):
    return {'prob': 0, 'origins': [], 'explored': explored, 'color': color}


if __name__ == "__main__":
    main()
