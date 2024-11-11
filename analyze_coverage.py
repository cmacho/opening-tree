import time
import chessgraph
import argparse
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
    args = parser.parse_args()
    color = args.color
    database = args.database

    if args.color == 'b':
        path = pathlib.Path("data/black")
    else:
        path = pathlib.Path("data/white")
    games_list = read_pgn_files_in_directory(path)
    graph = chessgraph.Graph(args.color, games_list)
    api_service = LichessExplorerService(database=database)
    position_probabilities = {}

    count_explored_positions = initialize_explored_positions(position_probabilities, graph)

    populate_probability_data(position_probabilities, api_service, graph, count_explored_positions)

    print(f"Number of positions with probabilities: {len(position_probabilities)}")

    now = datetime.now()
    datetime_string = now.strftime("%Y-%m-%d__%H_%M_%S")
    filename = "probabilities_" + color + "_" + database + "_" + datetime_string + ".txt"
    print_data(position_probabilities, filename)


def print_data(position_probabilities, filename):
    with open(filename, "a") as file:
        sorted_position_probs = sorted(position_probabilities.items(), key=lambda x: x[1]['prob'], reverse=True)
        for i, keyValuePair in enumerate(sorted_position_probs, start=1):
            print(f"{i}:", file=file)
            pretty_print_entry(keyValuePair[0], keyValuePair[1], file)
            print("", file=file)


def pretty_print_entry(fen, prob_entry, file):
    print(fen, file=file)
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


def populate_probability_data(position_probabilities, apiService, graph, count_explored_positions):
    initial_pos = chessgraph.relevant_fen_part(chess.STARTING_FEN)
    curr_idx = 0
    for curr_fen in graph.breadth_first(initial_pos):
        curr_idx += 1
        print(f"Processing position {curr_fen} which is the {curr_idx}th of {count_explored_positions} positions")
        curr_color = chessgraph.fen_to_color(curr_fen)
        if curr_color == graph.color:
            move_from_node = graph.get_moves(curr_fen)[0]
            next_fen = chessgraph.get_next_fen(curr_fen, move_from_node)
            position_probabilities[next_fen]['prob'] += position_probabilities[curr_fen]['prob']
        else:
            curr_list_of_uci = get_list_of_uci_moves(curr_fen, graph)
            time.sleep(1)  # respect rate limit (with sleep for only half a second, rate limit was exceeded)
            move_probs_list = apiService.get_move_probabilities(curr_list_of_uci)
            for move_prob in move_probs_list:
                next_fen = successor_fen(curr_fen, move_prob['uci'])
                if next_fen not in position_probabilities:
                    next_color = chessgraph.fen_to_color(next_fen)
                    position_probabilities[next_fen] = initialize_data_for_a_position(next_color, False)
                position_probabilities[next_fen]['prob'] += position_probabilities[curr_fen]['prob'] * move_prob['prob']
                if not graph.node_exists(next_fen):
                    add_origins_for_unexplored_position(curr_fen, next_fen, move_prob['uci'],
                                                        graph, position_probabilities)


def get_list_of_uci_moves(curr_fen, graph):
    if curr_fen == chessgraph.relevant_fen_part(chess.STARTING_FEN):
        return []
    first_origin = graph.get_first_origin(curr_fen)
    curr_list_of_uci = translate_origin_string_into_list_of_uci(first_origin)
    return curr_list_of_uci


def initialize_explored_positions(position_probabilities, graph):
    count = 0
    initial_pos = chessgraph.relevant_fen_part(chess.STARTING_FEN)
    for fen in graph.breadth_first(initial_pos):
        count += 1
        print(fen)
        position_probabilities[fen] = initialize_data_for_a_position(chessgraph.fen_to_color(fen), True)
        position_probabilities[fen]['origins'].extend(graph.get_origins(fen))
    position_probabilities[initial_pos]['prob'] = 1
    return count


def translate_origin_string_into_list_of_uci(origin_string):
    board = chess.Board()
    list_of_san_moves = chessgraph.build_list_of_san_moves_from_origin_string(origin_string)
    list_of_uci = []
    for san in list_of_san_moves:
        move = board.parse_san(san)
        list_of_uci.append(move.uci())
        board.push(move)
    return list_of_uci


def translate_list_of_uci_into_origin_string(uci_list):
    board = chess.Board()
    list_of_san = []
    for uci_move in uci_list:
        move = board.parse_uci(uci_move)
        list_of_san.append(board.san(move))
        board.push(move)
    return chessgraph.build_pgn_from_list_of_san_moves(list_of_san)


def successor_fen(fen_board, uci):
    board = chess.Board(fen_board)
    board.push(board.parse_uci(uci))
    return chessgraph.relevant_fen_part(board.fen())


def add_origins_for_unexplored_position(curr_fen, next_fen, uci_move, graph, position_probabilities):
    initial_board_position = chessgraph.relevant_fen_part(chess.STARTING_FEN)
    curr_origins = graph.get_origins(curr_fen)
    if len(curr_origins) == 0 and curr_fen == initial_board_position:
        curr_origins = [""]
    for origin in curr_origins:
        list_of_uci = translate_origin_string_into_list_of_uci(origin)
        list_of_uci.append(uci_move)
        new_origin = translate_list_of_uci_into_origin_string(list_of_uci)
        position_probabilities[next_fen]['origins'].append(new_origin)


def initialize_data_for_a_position(color, explored):
    return {'prob': 0, 'origins': [], 'explored': explored, 'color': color}


if __name__ == "__main__":
    main()
