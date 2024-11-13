
import chess
import chess.pgn
import queue
from util import relevant_fen_part, fen_to_color, get_next_fen
from util import build_list_of_san_moves_from_origin_string, build_pgn_from_list_of_san_moves


class Graph(object):
    """ a directed graph where nodes correspond to board positions and edges correspond to moves """
    def __init__(self, color, games, verbose=0):
        """
        Args:
            color: (string) Either "w" or "b". The color for which the graph will represent an opening book.
            For chess positions where this color is to move, there should always only be one move in the opening book.
            When the opposite color is to move, there can be multiple possible moves that are explored through the
            graph.
            games: (chess.pgn.Game) optional parameter. a list of chess.pgn.Game objects. Each game in the list is
            an opening tree loaded directly from a pgn using the chess.pgn library. If games is not the empty list, then
            the Graph is initialized with the data from the games.
            verbose: (int) controls the verbosity of the __init__ function. If verbose > 0, information is printed.
        """
        self.dict = {}
        self.color = color
        if len(games) > 0:
            if verbose > 0:
                print("consuming pgn data")
            for game in games:
                self.consume_pgn_game(game)
            self.saturate(verbose=verbose)
            if verbose > 0:
                print("finding origins.")
            self.find_origins()
            self.check_all_leaves_are_opponent_color()

    def add_moves(self, fen, move_list):
        """ Add the moves in move_list to the node corrsponding to the board position represented by fen. Create the
        node if it does not exist

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
        list_of_sans = []
        self.consume_subtree_of_pgn_game(game, list_of_sans)

    def consume_subtree_of_pgn_game(self, game_node, list_of_sans):
        """
        Add the data from subtree of a pgn game to the graph.

        Args:
            game_node: (chess.pgn.GameNode) a node in an opening tree loaded directly from a pgn file
            list_of_sans: (list) list of moves from the game that game_node belongs to that were executed in order
            to get to game_node. The moves are in SAN format
        """
        board = game_node.board()
        fen = relevant_fen_part(board.fen())
        move_list = [board.san(child.move) for child in game_node.variations]

        self.add_moves(fen, move_list)
        if len(list_of_sans) > 0:
            self.add_origin(fen, build_pgn_from_list_of_san_moves(list_of_sans), from_pgn=True)

        for child in game_node.variations:
            san = board.san(child.move)
            list_of_sans.append(san)
            self.consume_subtree_of_pgn_game(child, list_of_sans)
            list_of_sans.pop()

    def get_node(self, fen):
        """
        return the node corrsponding to fen

        Args:
            fen: (string) the fen representation of a board position which appears in the graph and therefore in
             self.dict. More specifically, fen is not in FEN format but in a reduced FEN format where the move clocks
             are not included

        Returns: (Node) returns the node corresponding to fen.
        """
        return self.dict[fen]

    def node_exists(self, fen):
        """ returns True if there is a node corresponding to fen, False otherwise"""
        return fen in self.dict

    def get_moves(self, fen):
        """ returns the explored moves for the position corresponding to fen

        Args:
             fen: (string) the fen representation of a board position which appears in the graph and therefore in
             self.dict. More specifically, fen is not in FEN format but in a reduced FEN format where the move clocks
             are not included
        Returns: (list) list of strings representing moves for position fen that are part of the graph.
         The moves are in SAN format.

        """
        node = self.get_node(fen)
        moves = node.get_moves()
        return moves

    def get_degree(self, fen):
        """ returns the number of moves at position fen that are part of the graph """
        node = self.get_node(fen)
        return node.get_degree()

    def add_origin(self, fen, origin_string, from_pgn=False):
        """ adds origin_string to the list of origins for the node corresponding to fen. If from_pgn == True, this
          indicates that the line comes directly from the pgn (and not from the graph computed from the pgn).
          This information is stored in the node's meta data.

          Args:
              fen: (string) the fen representation of a board position which appears in the graph and therefore in
             self.dict. More specifically, fen is not in FEN format but in a reduced FEN format where the move clocks
             are not included
              origin_string: (string) a series of moves in san format that leads to the current position
              from_pgn: (bool) True if the line represented by origin_string was found directly in pgn"""
        node = self.get_node(fen)
        node.add_origin(origin_string, from_pgn)

    def get_number_of_origins(self, fen):
        """ returns the number of origins and number of origins from pgn

        Args:
            fen: (string) the fen representation of a board position which appears in the graph and therefore in
                self.dict. More specifically, fen is not in FEN format but in a reduced FEN format where the move clocks
                are not included
        Returns:
            number_of_origins (int) the number of origins, i.e. number of lines in the opening graph that lead to
                the position
            num_origins_from_pgn (int) the number of origins that were found directly in pgn data
        """
        node = self.get_node(fen)
        number_of_origins, num_origins_from_pgn = node.get_number_of_origins()
        return number_of_origins, num_origins_from_pgn

    def print_origins(self, fen):
        """print the origins of the position, adding 'pgn' to indicate that a line was found directly in the pgn.

        Args:
             fen: (string) the fen representation of a board position which appears in the graph and therefore in
                self.dict. More specifically, fen is not in FEN format but in a reduced FEN format where the move clocks
                are not included
        """
        node = self.get_node(fen)
        node.print_origins()

    def get_first_origin(self, fen):
        """ returns the first origin string of the node corresponding to fen. Requires that fen is not the initial
        board position

        Args:
            fen: (string) the fen representation of a board position which appears in the graph and therefore in
                self.dict. More specifically, fen is not in FEN format but in a reduced FEN format where the move clocks
                are not included. fen must not be the initial board position.

        Returns:
            origin_string (string): the first origin string of the board position. It is guaranteed to be part of the
            pgn that was used to create the opening graph.
        """
        node = self.get_node(fen)
        origin_string = node.get_first_origin()
        return origin_string

    def get_origins(self, fen):
        """ returns the list of origins for the board position represented by fen

        Args:
            fen: (string) the fen representation of a board position which appears in the graph and therefore in
                self.dict. More specifically, fen is not in FEN format but in a reduced FEN format where the move clocks
                are not included. fen must not be the initial board position.

        Returns: (list) a list of strings. The strings represent the sequence of moves needed to get to the
         board position while staying within the graph. """
        node = self.get_node(fen)
        return node.get_origins()

    def saturate(self, verbose=0):
        """ completes the DAG represented by self by adding any opponent move for which the resulting position is
            already a node in self. This can be thought of as a kind of 'completion' or 'closure' operation.
            In other words, we add additional edges that we can get 'for free' without having to evaluate
            any positions.

            Args:
                verbose: (int) controls how much log information is printed.
            """
        if verbose > 0:
            print("saturating.")
        opposite_color_fens = [fen for fen in self.dict if fen_to_color(fen) != self.color]
        for fen in opposite_color_fens:
            board = chess.Board(fen)

            legal_moves = list(board.legal_moves)

            for move in legal_moves:
                san = board.san(move)
                board.push(move)
                resulting_fen = relevant_fen_part(board.fen())
                board.pop()
                if resulting_fen in self.dict and san not in self.get_moves(fen):
                    if verbose > 0:
                        print(f"Adding {san} to {fen}")
                    if verbose > 1:
                        print_board(fen)
                        print(" ")
                    self.add_moves(fen, [san])

    def find_origins(self):
        """ Adds the list of origins to each node in the graph. Here, origins means a sequence of moves through which
        the position could have been reached.
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
        if len(list_of_sans) > 0:
            self.add_origin(fen, build_pgn_from_list_of_san_moves(list_of_sans))

        for san in self.get_moves(fen):
            new_fen = get_next_fen(fen, san)
            list_of_sans.append(san)
            self.find_origins_in_subgraph(new_fen, list_of_sans)
            list_of_sans.pop()

    def breadth_first(self, fen):
        """  a generator that iterates through the graph breadt first, starting at fen.

        Args:
            fen: (string) A fen representation of a board position that appears in the graph. The root of the subtree
            to iterate through.

        Yields:
              curr_fen: (string) The fen representation of a board position that appears in the graph.
        """
        next_fens_to_look_at = queue.Queue()
        next_fens_to_look_at.put(fen)
        explored_fens = {fen}  # set of the fens that have already been looked at or added to queue

        while not next_fens_to_look_at.empty():
            curr_fen = next_fens_to_look_at.get()
            for san in self.get_moves(curr_fen):
                new_fen = get_next_fen(curr_fen, san)
                if new_fen not in explored_fens:
                    next_fens_to_look_at.put(new_fen)
                    explored_fens.add(new_fen)
            yield curr_fen

    def compute_stats(self, fen):
        """ Compute the number of nodes in the subgraph rooted at fen and the number of leaves in that subgraph

        Args:
            fen: (string) A fen representation of a board position such that fen is one of the keys of self.dict

        Returns:
            num_leaves (int) The number of leaves in the subgraph
            num_nodes (int) The number of nodes in the subgraph
        """
        num_leaves = 0
        num_nodes = 0
        for curr_fen in self.breadth_first(fen):
            num_nodes += 1
            if self.get_degree(curr_fen) == 0:
                assert len(self.get_moves(curr_fen)) == 0
                num_leaves += 1

        return num_leaves, num_nodes

    def check_all_leaves_are_opponent_color(self):
        for fen in self.dict:
            if self.get_degree(fen) == 0 and fen_to_color(fen) == self.color:
                origin = self.get_node(fen).origins[0]
                raise BadOpeningGraphError(f"Line {origin} ends in leaf of own color.")

    def number_of_moves(self, fen):
        """ returns the total number of moves that have been played to reach the position fen

        Args:
            fen (string): A fen representation of a board position such that fen is one of the keys of self.dict

        Returns:
            num_moves (int): The number of moves by both players that have been played in order to reach the position
        """
        fen = relevant_fen_part(fen)
        if fen == relevant_fen_part(chess.STARTING_FEN):
            return 0
        first_origin = self.get_first_origin(fen)
        list_of_sans = build_list_of_san_moves_from_origin_string(first_origin)
        return len(list_of_sans)


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
        self.num_pgn_origins = 0

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

    def get_moves(self):
        """
        returns the explored moves at the node

        Returns:
            (list) list of strings where each string represents a move in SAN format
        """
        return self.explored_moves.copy()

    def get_degree(self):
        """
        returns the number of outgoing edges at the node

        Returns: (int) out_degree of the node
        """
        assert self.out_degree == len(self.explored_moves)
        return self.out_degree

    def add_origin(self, origin_string, from_pgn=False):
        """ adds origin_string to the list of origins. If from_pgn == True, this
         indicates that the line comes directly from the pgn (and not from the graph
         computed from the pgn). Thus we increase num_pgn_origins by 1.

         Args:
             origin_string: (string) a series of moves in san format that leads to the current position
             from_pgn: (bool) True if the line represented by origin_string was found directly in pgn
         """
        if origin_string not in self.origins:
            self.origins.append(origin_string)
            if from_pgn:
                self.num_pgn_origins += 1

    def get_number_of_origins(self):
        """ returns the number of origins and number of origins from pgn

        Returns:
            number_of_origins (int) the number of origins, i.e. number of lines in the opening graph that lead to
            the position
            num_origins_from_pgn (int) the number of origins that were found directly in pgn data
        """
        return len(self.origins), self.num_pgn_origins

    def print_origins(self):
        """print the lines in self.origins, adding 'pgn' to indicate that a line was found directly in the pgn.
        This is determined based on num_pgn_origins """
        for i, s in enumerate(self.origins):
            if i < self.num_pgn_origins:
                print(s, "(pgn)")
            else:
                print(s)

    def get_first_origin(self):
        """ returns the first origin, if it exists. Otherwise, throw index error.
        Under normal circumstances, an origin should exist for every node except the root of the graph, which represents
        the initial board position.
    
        Returns:
            origin_string (string): the first origin for the node. It is guaranteed to be part of the pgn that was
            used to create the opening graph.
        """
        return self.origins[0]

    def get_origins(self):
        """ returns the list of origins

        Returns: (list) a list of strings. The strings represent the sequence of moves needed to get to the
         board position while staying within the graph. """
        return self.origins.copy()




def print_board(fen):
    """ print the board corresponding to the position described by fen

    Args:
        fen: (string) the FEN (Forsyth-Edwards-Notation) representation of a chess position. More specifically, the
            first four parts of a FEN, without the move-clocks
    """
    board = chess.Board(fen)
    print(board)


def test1():
    """ test case 1"""
    print(" ")
    print("Test case 1")
    with open("../test_data/good_opening_white.pgn") as pgn:
        game = chess.pgn.read_game(pgn)

    graph = Graph("w", [game])

    # get FEN of the position after 1. d4 d5
    board = chess.Board()
    board.push_san("d4")
    board.push_san("d5")
    fen = relevant_fen_part(board.fen())

    explored_moves = graph.get_moves(fen)
    print("Explored moves for position after 1. d4 d5")
    print(explored_moves)

    print("stats for this position:")
    num_leaves, num_nodes = graph.compute_stats(fen)
    print(f"num_leaves is {num_leaves} and num_nodes is {num_nodes}")

    # get next fen after executing the first move in the list of explored moves
    print("executing the first move from the list of explored moves.")
    next_fen = get_next_fen(fen, explored_moves[0])

    print("new position:")
    print_board(next_fen)
    print("explored moves for this new position:")
    explored_moves = graph.get_moves(next_fen)
    print(explored_moves)

    print("stats for this position:")
    next_num_leaves, next_num_nodes = graph.compute_stats(next_fen)
    assert next_num_leaves == num_leaves
    assert next_num_nodes == num_nodes - 1
    print(f"num_leaves is {next_num_leaves} and num_nodes is {next_num_nodes}")


def test2():
    """ test case 2"""
    print(" ")
    print("Test case 2")
    with open("../test_data/very_bad_opening_white.pgn") as pgn:
        game = chess.pgn.read_game(pgn)

    print("trying to consume very_bad_opening_white.pgn")

    try:
        _ = Graph("w", [game])
    except BadOpeningGraphError as err:
        print("successfully caught Error.")
        print("The error says:", err)
    else:
        raise Exception("should not reach here. BadOpeningGraphError was not successfully raised and caught")


def test3():
    """ test case 3 """
    print(" ")
    print("Test case 3")
    with open("../test_data/bad_opening_white.pgn") as pgn:
        game = chess.pgn.read_game(pgn)

    print("trying to consume bad_opening_white.pgn")

    try:
        _ = Graph("w", [game])
    except BadOpeningGraphError as err:
        print("successfully caught Error.")
        print("The error says:", err)
    else:
        raise Exception("should not reach here. BadOpeningGraphError was not successfully raised and caught")


def test4():
    """ test case 4: loading two good pgns with verbose=1 """
    print(" ")
    print("Test case 4")
    print("loading good_opening_black.pgn:")
    with open("../test_data/good_opening_black.pgn") as pgn:
        game = chess.pgn.read_game(pgn)
    _ = Graph("b", [game], verbose=1)

    print("loading good_opening_white.pgn:")
    with open("../test_data/good_opening_white.pgn") as pgn:
        game = chess.pgn.read_game(pgn)
    _ = Graph("w", [game], verbose=1)


def test5():
    """ test case 5 """
    print(" ")
    print("Test case 5")
    with open("../test_data/good_opening_white.pgn") as pgn:
        game = chess.pgn.read_game(pgn)
    graph = Graph("w", [game])

    fen = "rnbqkb1r/pp4pp/3ppn2/2p5/4P3/2N5/PPP2PPP/R1BQKBNR w KQkq -"
    print("getting origins for this position: ")
    print(fen)
    print("which looks like this:")
    print_board(fen)

    node = graph.get_node(fen)
    origins = node.origins
    print(f"number of origins is {len(origins)}")
    print("the origins are")
    graph.print_origins(fen)

    print(f"The explored_moves for the current position are {node.explored_moves} (should only be one)")

    num_leaves, num_nodes = graph.compute_stats(fen)
    print(f"The stats for the current position are")
    print(f"num_leaves: {num_leaves}, num_nodes: {num_nodes}")

    # another example based on output of Graph.saturate()
    board = chess.Board("rnbqkb1r/ppp2ppp/4pn2/3p4/2PP4/2N2N2/PP2PPPP/R1BQKB1R b KQkq -")
    board.push_san("Nc6")
    fen = relevant_fen_part(board.fen())

    print(f"getting origins for this position: {fen}")
    print("which looks like this:")
    print_board(fen)

    node = graph.get_node(fen)
    origins = node.origins
    print(f"number of origins is {len(origins)}")
    print("the origins are")
    node.print_origins()

    print(f"The explored_moves for the current position are {node.explored_moves}")

    num_leaves, num_nodes = graph.compute_stats(fen)
    print(f"The stats for the current position are")
    print(f"num_leaves: {num_leaves}, num_nodes: {num_nodes}")

    # a third example where there are more origins:
    fen = "rn1qkb1r/ppp1pppp/8/3n1b2/3P4/5N2/PP1NPPPP/R1BQKB1R b KQkq -"
    print(f"getting origins for this position: {fen}")
    print("which looks like this:")
    print_board(fen)

    node = graph.get_node(fen)
    origins = node.origins
    print(f"number of origins is {len(origins)}")
    print("the origins are")
    node.print_origins()

    print(f"The explored_moves for the current position are {node.explored_moves}")

    num_leaves, num_nodes = graph.compute_stats(fen)
    print(f"The stats for the current position are")
    print(f"num_leaves: {num_leaves}, num_nodes: {num_nodes}")


def test6():
    """ test case 6 """
    print(" ")
    print("Test case 6")
    with open("../test_data/good_opening_white.pgn") as pgn:
        game = chess.pgn.read_game(pgn)
    graph = Graph("w", [game])

    initial_fen = relevant_fen_part(chess.STARTING_FEN)
    num_leaves, num_nodes = graph.compute_stats(initial_fen)

    assert num_nodes == len(graph.dict)

    print("entire good_opening_white opening_book:")
    print("num_leaves", num_leaves)
    print("num_nodes", num_nodes)


def test7():
    """ test case 7: loading a pgn that contains a leaf of own color. """
    print(" ")
    print("Test case 7")
    with open("../test_data/bad_opening_black.pgn") as pgn:
        game = chess.pgn.read_game(pgn)

    print("trying to consume bad_opening_black.pgn")

    try:
        _ = Graph("b", [game])
    except BadOpeningGraphError as err:
        print("successfully caught Error.")
        print("The error says:", err)
    else:
        raise Exception("should not reach here. BadOpeningGraphError was not successfully raised and caught")


def run_tests():
    tests = [test1, test2, test3, test4, test5, test6, test7]
    for test in tests:
        test()


if __name__ == "__main__":
    run_tests()
