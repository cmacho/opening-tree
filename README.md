## Usage:

Run `explore_openings.py` from the command line by entering:
```
python explore_openings.py
```


## About:

This is an interactive command line tool for exploring, learning and practicing the preferred chess openings of the chess engine Leela Chess Zero ([Lc0](https://lczero.org/)). More specifically, we use the version of Lc0 that won the computer chess tournaments TCEC17 and CCC13 in 2020 (even though, in those tournaments, it could not use its own openings because openings were prescribed by the organizers of the tournament).

Every move by Black in in `data/black` and every move by White in `data/white` was calculated using Lc0, using the same neural network weights file ([384x30-t60-3010.pb.gz](https://lczero.org/play/networks/bestnets/)) that won the TCEC17 and CCC13 tournaments, and running 10,000,000 simulations (i.e. evaluating 10,000,000 nodes) in order to decide on each move. See Deepmind's [paper](https://kstatic.googleusercontent.com/files/2f51b2a749a284c2e2dfa13911da965f4855092a179469aedd15fbe4efe8f8cbf9c515ef83ac03a6515fa990e6f85fd827dcd477845e806f23a17845072dc7bd) on AlphaZero for more details on the Monte Carlo Tree Search algorithm used by Lc0 (which is essentially an open source version of AlphaZero).

The functionalities of the tool include:
- Transform the tree-like structure of the input data into a directed graph structure, thus consolidating information (see below for a more detailed explanation).
- Provide ways of exploring the data. 
- Allow the user to practice openings in practice mode.

### Transforming the input data

The input data is in `pgn` format. `pgn` data has a tree like structure where the same chess position may appear at multiple points in the tree. We transform this into a directed graph structure by collapsing multiple occurcence of the same chess position into one node. In this way, information can be consolidated. Here's an example:

The data in `data/black` may include the following two lines:

```
1. d4 Nf6 2. Bf4 d5 3. Nf3 e6 4. e3 c5
1. d4 Nf6 2. Nf3 e6 3. Bf4 c5 4. e3 d5 5. Nbd2 Qb6 6. Rb1 Bd6
```
However, the chess position after the first eight moves is the same in both lines. Thus, by collapsing these nodes into one, the resulting graph will also contain this opening:
```
1. d4 Nf6 2. Bf4 d5 3. Nf3 e6 4. e3 c5 5. Nbd2 Qb6 6. Rb1 Bd6
```

In other cases, we can even add moves that did not appear in the input data at all, because they result in explored chess positions. Example:
The input data in `data/white` may contain these two lines:
```
1. d4 Nf6 2. c4
1. d4 d5 2. c4 Nf6 3. Nf3
```
Since playing the move `2. ... d5` after `1. d4 Nf6 2. c4` will result in the same position as `1. d4 d5 2. c4 Nf6`, we can automatically add `d5` to the explored moves for the position after `1. d4 Nf6 2. c4` and the graph will then also contain this opening:
``` 
1. d4 Nf6 2. c4 d5 3. Nf3
```

### Exploring the data

The tool has two modes for exploring the data:
- In explore mode, you can navigate the tree / graph of chess openings. For every position where the opponent can make a move, you can see which moves are explored in our data, as well as some statistics about how many moves are explored after that move.
- In lookup mode, you can set up a position and then see whether it is part of the opening graph or not.

### Practice mode

In practice mode, the computer will pick one of the explored moves at random for every position where your opponent would usually make a move. You are then prompted to enter the correct move for the resulting position. When you either guess wrong or reach a leaf in the opening tree, the game starts over.


