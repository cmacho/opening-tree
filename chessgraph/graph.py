
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
            self.find_origins()

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

    def find_origins(self):
        """ Adds the list of origins to each node in the graph. Here, origins means a sequence of moves through which the
        position could have been reached.
        Requires that graph is nonempty.
        """
        list_of_sans = []
        initial_fen = relevant_fen_part(chess.STARTING_FEN)
        self.find_origins_in_subgraph(initial_fen, list_of_sans)

    def find_origins_in_subgraph(self, fen, list_of_sans):
        """  Adds the list of origins to each node in the subgraph rooted at fen.

        Args:
            fen: (string) A fen representation of a board position such that fen is one of the keys of self.dict
            list_of_sans: (list) list of strings. The strings represent he moves that led to the current position in
            SAN format
        """
        node = self.get_node(fen)
        assert node is not None
        node.add_origin(build_pgn_from_list_of_san_moves(list_of_sans))

        for san in node.explored_moves:
            new_fen = get_next_fen(fen, san)
            list_of_sans.append(san)
            self.find_origins_in_subgraph(new_fen, list_of_sans)
            list_of_sans.pop()


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
        self.origins = []

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

    def add_origin(self, origin_string):
        if origin_string not in self.origins:
            self.origins.append(origin_string)


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


def run_tests():
    ###############
    # Test case 1
    ###############
    print("Test case 1")
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
    print("Test case 2")
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
    print("Test case 3")
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
    print("Test case 4")
    pgn = open("../test_data/good_opening_black.pgn")
    game = chess.pgn.read_game(pgn)
    graph = Graph("b", game)

    ###############
    # Test case 5
    ###############
    print(" ")
    print("Test case 5")
    pgn = open("../test_data/good_opening_white.pgn")
    game = chess.pgn.read_game(pgn)
    graph = Graph("w", game)

    print("getting origins for this position: ")
    print("rnbqkb1r/pp4pp/3ppn2/2p5/4P3/2N5/PPP2PPP/R1BQKBNR w KQkq -")
    print("which looks like this:")
    print(chess.Board("rnbqkb1r/pp4pp/3ppn2/2p5/4P3/2N5/PPP2PPP/R1BQKBNR w KQkq -"))

    node = graph.get_node("rnbqkb1r/pp4pp/3ppn2/2p5/4P3/2N5/PPP2PPP/R1BQKBNR w KQkq -")
    origins = node.origins
    print(f"number of origins is {len(origins)}")
    print("the origins are")
    for s in origins:
        print(s)

    print(f"The explored_moves for the current position are {node.explored_moves} (should only be one)")

    #another example based on output of Graph.saturate():
    board = chess.Board("rnbqkb1r/ppp2ppp/4pn2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R b KQkq -")
    board.push_san("Nc6")
    fen = relevant_fen_part(board.fen())

    print(f"getting origins for this position: {fen}")
    print("which looks like this:")
    print(board)

    node = graph.get_node(fen)
    origins = node.origins
    print(f"number of origins is {len(origins)}")
    print("the origins are")
    for s in origins:
        print(s)

    for fen in graph.dict:
        if len(graph.dict[fen].origins) > 2:
            print(len(graph.dict[fen].origins), fen)

    # a third example where there are more origins:
    fen = "rn1qkb1r/ppp1pppp/8/3n1b2/3P4/5N2/PP1NPPPP/R1BQKB1R b KQkq -"
    print(f"getting origins for this position: {fen}")
    print("which looks like this:")
    print(chess.Board(fen))

    node = graph.get_node(fen)
    origins = node.origins
    print(f"number of origins is {len(origins)}")
    print("the origins are")
    for s in origins:
        print(s)



# test the module
if __name__ == "__main__":
    run_tests()
