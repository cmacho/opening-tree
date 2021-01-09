import chessgraph
import chess
import chess.pgn
import random

def check_exit(user_input):
    """ checks whether the string user_input is 'exit' or 'quit'. If so, exits

    Args:
    user_input (string) a string entered by the user
    """
    if user_input in ['exit', 'quit']:
        exit(0)


def ask_for_input(prompt, options):
    """ Repeatedly print prompt asking for user input until user inputs one of the strings in option or enters 'exit'.
    If user entered one of the strings in options, return the user input

    Args:
        prompt (string): The prompt asking the user for input
        options (list): list of strings
    Returns:
        the option selected by the user
    """
    prompt_to_print = prompt + '\n'
    lowercase_options = [s.lower() for s in options]
    while True:
        user_input = input(prompt_to_print)
        orig_user_input = user_input.strip()
        user_input = user_input.lower().strip()
        check_exit(user_input)
        if user_input == "":
            prompt_to_print = ""  # allow user to create white space by entering empty string
        elif user_input in lowercase_options:
            break
        else:
            print(f"Could not parse '{orig_user_input}'. Enter 'exit' in order to exit the program. \n")
            prompt_to_print = prompt + '\n'
    for i, s in enumerate(lowercase_options):
        if user_input == s:
            return options[i]
    raise Exception(f"should not reach here. user_input is {user_input}. options is {options}.")


def ask_to_enter_anything(prompt, options):
    lowercase_options = [s.lower() for s in options]
    user_input = input(prompt + '\n')
    user_input = user_input.lower().strip()
    check_exit(user_input)
    for i, s in enumerate(lowercase_options):
        if user_input == s:
            return options[i]
    return None


def main():
    """ask user for options and then run corresponding part of the program"""
    print("Enter 'exit' at any time in order to exit the program.")
    params = {}
    params['fen'] = chessgraph.relevant_fen_part(chess.STARTING_FEN)
    params['mode'] = ask_for_input("Choose mode. Either 'practice' or 'explore'. or 'lookup'.",
                                   ['practice', 'explore', 'lookup'])
    color = ask_for_input(f"Enter 'b' or 'w' to indicate which color you want play as",
                          ['b', 'w'])
    params['list_of_sans'] = []

    if color == 'b':
        pgn = open("data/opening_black.pgn")
    else:
        pgn = open("data/opening_white.pgn")
    game = chess.pgn.read_game(pgn)
    params['graph'] = chessgraph.Graph(color, game)

    start_mode_based_on_options(params)


def start_mode_based_on_options(params):
    """ start either explore mode, practice mode or lookup mode, depending on params['mode'], with the specified
    options in params. Switch into next mode when the chosen mode returns new params. """
    while True:
        if params['mode'] == 'explore':
            params = explore_tree(params)
        elif params['mode'] == 'practice':
            params = practice_openings(params)
        elif params['mode'] == 'lookup':
            params = look_up_position(params)
        else:
            raise Exception(f"should not reach here. Options is {params}.")


def explore_tree(params):
    """ explore the opening tree interactively

    Args:
        params (dict): parameters
    """
    initial_fen = chessgraph.relevant_fen_part(chess.STARTING_FEN)
    fen = params['fen']
    list_of_sans = params['list_of_sans'].copy()
    board = chess.Board()

    stack = []
    if len(list_of_sans) > 0:
        for san in list_of_sans:
            board.push_san(san)
            stack.append(chessgraph.relevant_fen_part(board.fen()))
        #  remove last entry of stack and compare it to fen:
        last_entry = stack.pop()
        assert last_entry == fen

    skip_print = False
    graph = params['graph']

    while True:
        if not skip_print:
            print_basic_position_information(graph, fen, list_of_sans, include_number_of_origins=True)

        general_options = ['b', 'origin', 'lookup', 'practice']
        general_prompts = "Enter 'b' to go back to previous position.\n" \
                          "Enter 'origin' to print the origins of this position. " \
                          "Enter 'lookup' in order to look up a position. " \
                          "Enter 'practice' in order to practice from this position."
        if chessgraph.fen_to_color(fen) == graph.color:
            skip_print = False
            if fen == initial_fen:
                user_input = None  # go directly to position after first move
            else:
                print_which_color_to_move(fen)
                prompt = "Press Enter to continue." + " " + general_prompts
                options = general_options
                user_input = ask_to_enter_anything(prompt, options)
            if user_input is None:
                moves = graph.get_moves(fen)
                assert len(moves) == 1
                san = moves[0]
                stack.append(fen)
                list_of_sans.append(san)
                fen = chessgraph.get_next_fen(fen, san)
                continue
        else:  # chessgraph.fen_to_color(fen) != graph.color
            print_which_color_to_move(fen)
            prompt = "Enter one of the moves in SAN format in order to execute the move." + " " + general_prompts
            if not skip_print and graph.get_degree(fen) > 0:
                print_explored_moves_and_statistics(graph, fen)
            elif graph.get_degree(fen) == 0:
                print("Reached leaf in opening graph. No more moves explored.")
                prompt = general_prompts
            skip_print = False
            options = graph.get_moves(fen) + general_options
            user_input = ask_for_input(prompt, options)
            if user_input in graph.get_moves(fen):
                stack.append(fen)
                list_of_sans.append(user_input)
                fen = chessgraph.get_next_fen(fen, user_input)
                continue
        if user_input == 'b':
            if len(stack) > 0:
                fen = stack.pop()
                list_of_sans.pop()
            else:
                print("Cannot go back since this is the starting position.")
                skip_print = True
            continue
        elif user_input == 'origin':
            print("Lines leading to this positon:")
            graph.print_origins(fen)
            print(" ")
            skip_print = True
            continue
        elif user_input == 'lookup':
            params['mode'] = 'lookup'
            params['fen'] = fen
            params['list_of_sans'] = list_of_sans
            return params
        elif user_input == 'practice':
            params['mode'] = 'practice'
            params['fen'] = fen
            params['list_of_sans'] = list_of_sans
            return params
        else:
            raise Exception(f"Should not reach here. Variable user_input has value {user_input}.")


def practice_openings(params):
    """
    practice openings. Moves for opponent are chosen at random and user is asked to enter correct moves for their
    own pieces.

    Args:
        params (string): parameters
    """
    graph = params['graph']
    fen = params['fen']
    list_of_sans = params['list_of_sans'].copy()
    general_options = ['restart', 'explore', 'lookup']
    while True:
        if chessgraph.fen_to_color(fen) == graph.color:
            print_basic_position_information(graph, fen, list_of_sans)
            move_list = graph.get_moves(fen)
            correct_san = move_list[0]
            legal_moves = list_of_legal_moves(fen)
            assert correct_san in legal_moves
            options = legal_moves + general_options
            prompt = "Enter your move.\n" \
                     "Or enter 'restart' to restart. Enter 'explore' or 'lookup' to switch to a different mode."
            user_input = ask_for_input(prompt, options)

            if user_input == correct_san:
                fen = chessgraph.get_next_fen(fen, correct_san)
                list_of_sans.append(correct_san)
                continue

            elif user_input in legal_moves:
                print(f"{user_input} is wrong. The correct move is {correct_san}.")
                user_input = ask_to_enter_anything("Press enter to continue.", general_options)
                if user_input is None:
                    user_input = 'restart'

        else:  # opponent's move
            # opponent chooses move at random where the probability for each choice is proportional to the number
            # of leaves in the subgraph corresponding to that choice
            print_basic_position_information(graph, fen, list_of_sans)
            if graph.get_degree(fen) > 0:
                move_list = graph.get_moves(fen)
                stats = stats_for_moves(graph, fen)
                weights = [stats[san][1] for san in move_list]
                san = weighted_random_choice(move_list, weights)

                fen = chessgraph.get_next_fen(fen, san)
                list_of_sans.append(san)
                continue
            else:
                print("Success!! You reached a leaf. There are no more explored moves in this line.")
                user_input = ask_to_enter_anything("Press enter to continue.", general_options)
                if user_input is None:
                    fen = params['fen']
                    list_of_sans = params['list_of_sans'].copy()
                    continue

        assert user_input is not None
        if user_input == 'restart':
            fen = params['fen']
            list_of_sans = params['list_of_sans'].copy()
            continue
        elif user_input == 'explore':
            params['mode'] = 'explore'
            params['fen'] = fen
            params['list_of_sans'] = list_of_sans
            return params
        elif user_input == 'lookup':
            params['mode'] = 'lookup'
            params['fen'] = fen
            params['list_of_sans'] = list_of_sans
            return params
        else:
            raise Exception(f"Should not reach here. user_input is {user_input}")


def look_up_position(params):
    graph = params['graph']
    list_of_sans = params['list_of_sans']
    fen = params['fen']

    board = chess.Board()
    for san in list_of_sans:
        board.push_san(san)

    skip_print_and_lookup = False

    while True:
        if not skip_print_and_lookup:
            print_basic_position_information(graph, fen, list_of_sans, include_number_of_origins=False)
            if graph.color == 'w':
                color_word = 'white'
            else:
                color_word = 'black'
            question = "Is position part of " + color_word + " opening graph?"
            if graph.node_exists(fen):
                print(question, "Yes.")
                print("Enter 'explore' to enter exploration mode. Enter 'practice' to practice from this position.\n"
                      "Enter 'origin' in order to see origins for this position.")
                options = ['practice', 'origin', 'explore', 'b'] + list_of_legal_moves(fen)
            else:
                print(question, "No.")
                options = ['b'] + list_of_legal_moves(fen)
        skip_print_and_lookup = False
        prompt = "Enter a move in SAN format. Enter 'b' to go back. "
        user_input = ask_for_input(prompt, options)

        if user_input in list_of_legal_moves(fen):
            board.push_san(user_input)
            list_of_sans.append(user_input)
            fen = chessgraph.relevant_fen_part(board.fen())
        elif user_input == 'b':
            if len(list_of_sans) > 0:
                list_of_sans.pop()
                board.pop()
                fen = chessgraph.relevant_fen_part(board.fen())
            else:
                print("Cannot go back. This is already the starting position.")
        elif user_input == 'origin':
            print("Lines leading to this positon:")
            graph.print_origins(fen)
            print(" ")
            skip_print_and_lookup = True
        else:
            assert graph.node_exists(fen)
            params['fen'] = fen
            # since current list_of_sans may not be part of opening tree, parse new list of sans from origin string
            if len(list_of_sans) > 0:
                origin_string = graph.get_first_origin(fen)
                params['list_of_sans'] = chessgraph.build_list_of_san_moves_from_origin_string(origin_string)
            else:
                params['list_of_sans'] = []
            if user_input == 'practice':
                params['mode'] = 'practice'
            elif user_input == 'explore':
                params['mode'] = 'explore'
            else:
                raise Exception(f"Should not reach here. user_input is {user_input}.")
            return params


def print_basic_position_information(graph, fen, list_of_sans, include_number_of_origins=False):
    """ print basic information about the position """
    print("========================================================================")
    if len(list_of_sans) > 0:
        print(chessgraph.build_pgn_from_list_of_san_moves(list_of_sans))
    else:
        print("Initial position.")
    print("FEN:", fen)
    print("========================================================================")
    if len(list_of_sans) > 0 and include_number_of_origins:
        num_origins, _ = graph.get_number_of_origins(fen)
        print(f"The number of lines leading to this position (number of origins) is {num_origins}.")


def print_which_color_to_move(fen):
    """ print a message stating which player is to move in the position represented by fen

    Args:
        fen: (string) the fen representation of a board position. Can also be only the first parts of a FEN, without
        the move clocks.
    """
    color = chessgraph.fen_to_color(fen)
    if color == 'w':
        print("White to move.")
    elif color == 'b':
        print("Black to move.")
    else:
        raise Exception(f"Should not reach here. Variable color has value {color}.")


def print_explored_moves_and_statistics(graph, fen):
    """ print the explored moves in graph for position fen as well as the number of children,
    leaves and nodes below the nodes resulting from the move. Since this function is always called
    with fen representing a position of color != graph.color, the positions arising after making
    a move have only one child, each. Therefore we print the number of children that child instead
    of printing '1' as number of children for every move (which would not be informative). """
    print("Explored moves:")
    moves = graph.get_moves(fen)
    stats = stats_for_moves(graph, fen)
    moves.sort(key=lambda x: stats[x][1], reverse=True)
    for i, san in enumerate(moves):
        num_children, num_leaves, num_nodes = stats[san]
        print(f"{i+1:2}) {san:3}  [children: {num_children:3}, "
              f"leaves: {num_leaves:3}, nodes: {num_nodes:3}]")


def stats_for_moves(graph, fen):
    """  for each of the explored moves at the position specified by fen, compute number of children, as well as
    number of leaves and number of nodes in the subtree rooted at the node. Return a dictionary containing this
    information

    Args:
        graph (chessgraph.Graph): the opening graph we are considering
        fen (string): the fen representation of a board position that appears in graph

    Returns:
        stats (dict): keys are explored moves in SAN notation. values are triples (num_children, num_leaves, num_nodes)
    """
    stats = {}
    moves = graph.get_moves(fen)
    for i, san in enumerate(moves):
        new_fen = chessgraph.get_next_fen(fen, san)
        new_san = graph.get_moves(new_fen)[0]
        new_new_fen = chessgraph.get_next_fen(new_fen, new_san)
        num_children = graph.get_degree(new_new_fen)
        num_leaves, num_nodes = graph.compute_stats(new_fen)
        stats[san] = (num_children, num_leaves, num_nodes)
    return stats


def list_of_legal_moves(fen):
    """ returns a list of all legal moves for the position in SAN format

    Args:
        fen: (string) the FEN (Forsyth-Edwards-Notation) representation of a chess position. More specifically, the
              first four parts of a FEN, without the move-clocks
    Returns:
        (list) a list of strings, each one the SAN representation of a legal move for the position
    """
    board = chess.Board(fen)
    return [board.san(move) for move in board.legal_moves]


def weighted_random_choice(choices, weights):
    """ returns one of the elements of choices at random where the probability for each choices[i] is proportional to
    weights[i]"""
    random_number = random.random()
    total_weight = sum(weights)
    aggregate = 0
    for i, element in enumerate(choices):
        aggregate = aggregate + weights[i]
        if aggregate / total_weight > random_number:
            return element
    raise Exception(f"should not reach here. weights is {weights}.")

if __name__ == "__main__":
    main()
