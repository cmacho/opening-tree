import chess


def read_pgn_files_in_directory(path):
    """ returns a list of chess.pgn.Game objects, one for each pgn file in path, containing the data from the
    pgn files.

    Args:
        path: a pathlib.Path object. The path for the directory from which we want to read pgn files
    Returns:
        games_list: (list) list of chess.pgn.Game objects
    """
    list_data_dir = list(path.glob("*"))
    games_list = []
    for file_path in list_data_dir:
        with open(file_path) as pgn:
            game = chess.pgn.read_game(pgn)
            games_list.append(game)
    return games_list

def fen_to_color(fen):
    """ Extract the color of whose turn it is from a fen representation of a board position

    Args:
        fen: (string) the fen representation of a board position. Can also be only the first parts of a FEN, without
        the move clocks.

    Returns: (string) "b" if it is black'r turn or "w" if it is white's turn
    """
    parts = fen.split()
    turn_part = parts[1]
    return turn_part


def relevant_fen_part(fen):
    """ Reduces a fen to the first parts without the number of moves and number of moves since last capture (also
    known as move clocks)

    Args:
        fen: (string) a full FEN such as "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2"
    Returns: (string) the relevant part of the FEN, e.g. "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq -"
    """
    parts = fen.split()
    relevant_parts = parts[:4]
    separator = ' '
    new_fen = separator.join(relevant_parts)
    return new_fen


def get_next_fen(fen, san):
    """
    Returns the next board position after executing the move represented by san in the position represented by fen

    Args:
        fen: (string) current board position in FEN format. More specifically, the first four parts of a FEN,
        without the move-clocks
        san: (string) move in SAN format
    Returns: (string) the next board position in fen format. More specifically, the first four parts of a FEN,
        without the move-clocks
    """
    board = chess.Board(fen)
    board.push_san(san)
    new_full_fen = board.fen()
    return relevant_fen_part(new_full_fen)


def build_pgn_from_list_of_san_moves(list_of_sans):
    """ builds a list of moves in SAN format into a single string containing all the moves with numbers for turns

    Args:
        list_of_sans: (list) a list of strings, each representing a move in SAN format. The moves should constitute a
        legal chess game starting from the initial position
    Returns: (string) a string where all the moves in list_of_sans are combined into one string and numbers are
    added for turns. In other words, the string represents the game in standard algebraic notation.
    """
    if len(list_of_sans) == 0:
        return ""

    new_list = []
    count = 0
    for ii in range(len(list_of_sans)):
        if ii % 2 == 0:
            count += 1
            new_list.append(str(count) + ".")
        new_list.append(list_of_sans[ii])
    return " ".join(new_list)


def build_list_of_san_moves_from_origin_string(origin_string):
    """ parses a string that represents a sequence of moves into a list containing the sequence of moves

    Args:
        origin_string (string): the first few moves of a possible chess game in pgn format. However, in contrast to
        more general pgns, no branching is allowed here.
    Return:
        list_of_sans (list): the elements of the list are strings. The strings are the same chess moves in SAN format
        as the ones in origin_string.
    """
    list_of_sans = []
    tokens = origin_string.split()
    for token in tokens:
        if not token[0].isnumeric():
            list_of_sans.append(token)
    return list_of_sans

def translate_origin_string_into_list_of_uci(origin_string):
    board = chess.Board()
    list_of_san_moves = build_list_of_san_moves_from_origin_string(origin_string)
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
    return build_pgn_from_list_of_san_moves(list_of_san)


def successor_fen(fen_board, uci):
    board = chess.Board(fen_board)
    board.push(board.parse_uci(uci))
    return relevant_fen_part(board.fen())
