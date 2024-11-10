import requests


class LichessExplorerClient:
    def __init__(self, database="lichess"):
        """

        - database (str): Either "lichess" or "master". Which database to use, i.e.
            either lichess games or master games.
        - variant (str): The variant of chess to explore. Default is 'standard'.
        - speeds (list of str): List of game speeds, e.g., ["blitz", "rapid"].
        - ratings (list of int): List of rating groups, e.g., [1200, 1600].
        - moves (int): Number of most common moves to display. Default is 12.
        - topGames (int): Number of top games to display. Max is 4.
        - recentGames (int): Number of recent games to display. Max is 4.
        - history (bool): Optionally retrieve history. Default is False.
        """
        if database == "lichess":
            self.base_url = "https://explorer.lichess.ovh/lichess"
            self.moves = 100
            self.variant = "standard"
            self.ratings = [1000, 1200, 1400, 1600, 1800, 2000, 2200, 2500]
            self.speeds = ["bullet", "blitz", "rapid", "classical", "correspondence"]
        elif database == "master":
            self.base_url = "https://explorer.lichess.ovh/master"
            self.moves = 100
            self.variant = None
            self.ratings = None
            self.speeds = None
        else:
            raise Exception("Invalid value for database parameter: " + database)

    def get_stats(self, play=None):
        """
        Retrieve move statistics for the given position.

        Parameters:
        - play (str): Comma-separated sequence of legal moves in UCI notation.

        Returns:
        - dict: JSON response from the Lichess API.
        """
        # Build query parameters dictionary
        params = {
            "variant": self.variant,
            "play": play,
            "speeds": ",".join(self.speeds) if self.speeds else None,
            "ratings": ",".join(map(str, self.ratings)) if self.ratings else None,
            "moves": self.moves,
            "topGames": 0,
            "recentGames": 0,
        }

        # Remove any parameters that are None (not provided)
        params = {k: v for k, v in params.items() if v is not None}

        # Make GET request to the API
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()  # Raise an error for bad HTTP status
            return response.json()  # Return response JSON as a dictionary
        except requests.RequestException as e:
            print(f"An error occurred: {e}")
            return None


# Example usage:
if __name__ == "__main__":
    client = LichessExplorerClient(
        database="master"
    )
    result = client.get_stats(
        play="d2d4,d7d5,c2c4"
    )
    print("From master database:")
    print(result)
    print(f"Result[white] is {result['white']}")
    print(f"Number of moves is {len(result['moves'])}")


    client = LichessExplorerClient(
        database="lichess"
    )
    result = client.get_stats(
        play="d2d4,d7d5,c2c4"
    )
    print("From lichess games database:")
    print(result)
    print(f"Result[white] is {result['white']}")
    print(f"Number of moves is {len(result['moves'])}")
