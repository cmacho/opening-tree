
import chess
import chess.pgn


class Graph(object):
    """ a directed graph where nodes correspond to board positions and edges correspond to moves """
    def __init__(self, color, game=None):
        """
        Args:
            color: (string) Either "w" or "b". The color for which the graph will represent an opening book.
            For chess positions where this color is to move, there should always only be one move in the opening book.
            When the opposite color is to move, there can be multiple possible moves that are explored through the
            graph.
            game: (chess.pgn.Game) optional parameter. an opening tree loaded directly from a pgn using the chess.pgn
            library. If this argument is not None, then the Graph is initialized with the data from game.
        """
        self.dict = {}
        self.color = color
        if game is not None:
            self.consume_pgn_game(game)
            self.saturate()

    def add_node_moves(self, fen, move_list):
        """ Add the moves in move_list to the node corrsponding to the board position represented by fen

        Args:
            fen: (string) the FEN (Forsyth-Edwards-Notation) representation of a chess position. More specifically, the
            first four parts of a FEN, without the move-clocks
            move_list: (list)a list of strings where each one is a chess move in SAN format (Standard Algebraic
            Notation)
        Raises: BadOpeningGraphError if after adding the moves, there are more than one moves for the position where
        the player of color self.color is to move.
        """
        if fen in self.dict:
            self.dict[fen].add_moves(move_list)
        else:
            self.dict[fen] = Node(move_list)

        if fen_to_color(fen) == self.color and self.dict[fen].out_degree > 1:
            raise BadOpeningGraphError(f"There is more than one move for position {fen} "
                                       f"in opening book for color {self.color}. Namely there are these:"
                                       f"{self.dict[fen].explored_moves}")

    def consume_pgn_game(self, game):
        """
        Add the data from game to the graph.

        Args:
            game: (chess.pgn.Game) An opening tree loaded directly from a pgn file
        """
        self.consume_subtree_of_pgn_game(game)

    def consume_subtree_of_pgn_game(self, game_node):
        """
        Add the data from subtree of a pgn game to the graph.

        Args:
            game_node: (chess.pgn.GameNode) a node in an opening tree loaded directly from a pgn file
        """
        board = game_node.board()
        fen = relevant_fen_part(board.fen())
        move_list = [board.san(child.move) for child in game_node.variations]

        self.add_node_moves(fen, move_list)

        for child in game_node.variations:
            self.consume_subtree_of_pgn_game(child)

    def get_node(self, fen):
        """
        If a node for fen exists in self, return that node. Else return None.

        Args:
            fen: (string) the fen representation of a board position. Can also be only the first parts of a FEN, without
            the move clocks.

        Returns: (Node OR None) returns the node corresponding to fen if it exists, otherwise returns None.
        """
        if fen in self.dict:
            return self.dict[fen]
        else:
            return None

    def saturate(self):
        """ completes the DAG represented by self by adding any opponent move for which the resulting position is
            already a node in self. This can be thought of as a kind of 'completion' or 'closure' operation.
            In other words, we add additional edges that we can get 'for free' without having to evaluate
            any positions. """
        print("saturating.")
        opposite_color_fens = [fen for fen in self.dict if fen_to_color(fen) != self.color]
        for fen in opposite_color_fens:
            node = self.get_node(fen)
            assert node is not None
            board = chess.Board(fen)

            legal_moves = list(board.legal_moves)

            for move in legal_moves:
                san = board.san(move)
                board.push(move)
                resulting_fen = relevant_fen_part(board.fen())
                board.pop()
                if resulting_fen in self.dict and san not in node.explored_moves:
                    print(f"Adding {san} to {fen}")
                    node.add_moves([san])


class BadOpeningGraphError(Exception):
    pass


class Node(object):
    """ a Node for a directed graph, storing information about edges (moves) and various extra information """
    def __init__(self, move_list):
        """
        Args:
            move_list: (list) a list of strings where each one is a chess move in SAN format (Standard Algebraic
            Notation)
        """
        self.explored_moves = move_list.copy()
        self.out_degree = len(self.explored_moves)

    def add_moves(self, move_list):
        """ Add the moves in move_list to the explored moves for the chess position represented by the node,
        if they are not already there

        Args:
            move_list: (list) a list of strings where each one is a chess move in SAN format (Standard Algebraic
            Notation)
        """
        for move in move_list:
            if move not in self.explored_moves:
                self.explored_moves.append(move)
        self.out_degree = len(self.explored_moves)


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


def run_tests():
    ###############
    # Test case 1
    ###############
    pgn = open("../test_data/good_opening_white.pgn")
    game = chess.pgn.read_game(pgn)

    graph = Graph("w", game)

    # get FEN of the position after 1. d4 d5
    board = chess.Board()
    board.push_san("d4")
    board.push_san("d5")
    fen = relevant_fen_part(board.fen())

    node = graph.dict[fen]
    explored_moves = node.explored_moves
    print("Explored moves for position after 1. d4 d5")
    print(explored_moves)

    # get next fen after executing the first move in the list of explored moves
    print("executing the first move from the list.")
    next_fen = get_next_fen(fen, explored_moves[0])

    new_node = graph.dict[next_fen]
    print("new position:")
    print(chess.Board(next_fen))
    print("explored moves for this new position:")
    explored_moves = new_node.explored_moves
    print(explored_moves)

    ###############
    # Test case 2
    ###############
    print(" ")
    pgn = open("../test_data/very_bad_opening_white.pgn")
    game = chess.pgn.read_game(pgn)

    print("trying to consume very_bad_opening_white.pgn")

    try:
        graph = Graph("w", game)
    except BadOpeningGraphError as err:
        print("successfully caught Error.")
        print("The error says:", err)
    else:
        raise Exception("should not reach here. BadOpeningGraphError was not successfully raised and caught")

    ###############
    # Test case 3
    ###############
    print(" ")
    pgn = open("../test_data/bad_opening_white.pgn")
    game = chess.pgn.read_game(pgn)

    print("trying to consume bad_opening_white.pgn")

    try:
        graph = Graph("w", game)
    except BadOpeningGraphError as err:
        print("successfully caught Error.")
        print("The error says:", err)
    else:
        raise Exception("should not reach here. BadOpeningGraphError was not successfully raised and caught")

    ###############
    # Test case 4
    ###############
    print(" ")
    pgn = open("../test_data/good_opening_black.pgn")
    game = chess.pgn.read_game(pgn)
    graph = Graph("b", game)


# test the module
if __name__ == "__main__":
    run_tests()
