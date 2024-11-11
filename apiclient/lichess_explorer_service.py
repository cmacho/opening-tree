from apiclient.lichess_explorer_client import LichessExplorerClient


class LichessExplorerService:

    def __init__(self, database="lichess"):
        """
        Parameters:
        - database (str): Either "lichess" or "master". Which database to use, i.e.
            either lichess games or master games.
        """
        self.api_client = LichessExplorerClient(database=database)

    def get_move_probabilities(self, list_of_uci_moves):
        """
        Retrieve Lichess game data based on specified filters.

        Parameters:
        - play (str): Comma-separated sequence of legal moves in UCI notation.

        Returns:
        - list: list of dictionaries, each one containing
            - 'uci' : a move in UCI format
            - 'prob': the probability that the move was played starting from the current position
        """
        play = ",".join(list_of_uci_moves)
        response = self.api_client.get_stats(play)
        move_stats = response['moves']
        total = response['white'] + response['black'] + response['draws']
        result = []
        for move in move_stats:
            curr = {'uci': move['uci']}
            curr_move_total = move['white'] + move['black'] + move['draws']
            curr['prob'] = curr_move_total / total
            result.append(curr)
        return result

if __name__ == "__main__":
    service = LichessExplorerService("lichess")
    result = service.get_move_probabilities(['d2d4','d7d5','c2c4'])
    for move in result:
        print(move)

