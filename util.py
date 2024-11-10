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
