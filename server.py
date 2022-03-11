from rich import print
from rich.console import Console
from rich.table import Table

from core import Champion, Match, Shape, Team
from socket import AF_INET, SO_REUSEADDR, SOCK_STREAM, socket
from ssl import SOL_SOCKET

from enumValues import FINISHED, INPUT, INFO, GET_CHAMPTIONS, GET_HISTORY_FORM_DATABASE, SEND_HISTORY_TO_DATABASE

import pickle

buffer = 10


def send_to_player(num, message):
    connections[num].send(INFO + message.encode() + FINISHED)


def send_to_everyone(message):
    for sock in connections:
        sock.send(INFO + message.encode() + FINISHED)


def request_input(num, message):
    connections[num].send(INPUT + message.encode() + FINISHED)
    return recieve_data(num)


def recieve_data(num):
    while True:
        data = connections[num].recv(1024)
        if data:
            return data.decode()


def storeMatch(match: Match):
    print(match)
    msg = pickle.dumps(match)
    msg = bytes(f"{len(msg):<{buffer}}", "utf-8") + msg
    databaseSocket.send(SEND_HISTORY_TO_DATABASE)
    databaseSocket.send(msg)


def getChamps():
    msg = GET_CHAMPTIONS
    databaseSocket.send(msg)
    fullResponse = b""
    firstIter = True
    while True:
        response = databaseSocket.recv(1024)
        if firstIter:
            print("Got champs from DB")
            msglen = int(response[:buffer])
            firstIter = False

        fullResponse += response
        if len(fullResponse) - buffer == msglen:
            print("Got all the champs")

            champs = pickle.loads(fullResponse[buffer:])
            return champs


def print_available_champs(champions: dict[Champion]) -> None:
    # Create a table containing available champions
    available_champs = Table(title='Available champions')

    # Add the columns Name, probability of rock, probability of paper and
    # probability of scissors
    available_champs.add_column("Name", style="cyan", no_wrap=True)
    available_champs.add_column("prob(:raised_fist-emoji:)", justify="center")
    available_champs.add_column("prob(:raised_hand-emoji:)", justify="center")
    available_champs.add_column("prob(:victory_hand-emoji:)", justify="center")

    # Populate the table
    for champion in champions.values():
        available_champs.add_row(*champion.str_tuple)

    console = Console(force_terminal=False)
    with console.capture() as capture:
        console.print(available_champs)

    send_to_everyone(capture.get())
    print(capture.get())


def input_champion(playerId: int,
                   prompt: str,
                   color: str,
                   champions: dict[Champion],
                   player1: list[str],
                   player2: list[str]) -> None:
    # Prompt the player to choose a champion and provide the reason why
    # certain champion cannot be selected
    while True:
        match request_input(playerId, f'[{color}]{prompt}'):
            case name if name not in champions:
                send_to_player(playerId, f'The champion {name} is not available. Try again.')
            case name if name in player1:
                send_to_player(playerId, f'{name} is already in your team. Try again.')
            case name if name in player2:
                send_to_player(playerId, f'{name} is in the enemy team. Try again.')
            case _:
                player1.append(name)
                send_to_everyone(f"Player {playerId + 1} chose {name}!")
                break


def print_match_summary(match: Match) -> None:
    EMOJI = {
        Shape.ROCK: ':raised_fist-emoji:',
        Shape.PAPER: ':raised_hand-emoji:',
        Shape.SCISSORS: ':victory_hand-emoji:'
    }

    # For each round print a table with the results
    for index, round in enumerate(match.rounds):

        # Create a table containing the results of the round
        round_summary = Table(title=f'Round {index + 1}')

        # Add columns for each team
        round_summary.add_column("Red",
                                 style="red",
                                 no_wrap=True)
        round_summary.add_column("Blue",
                                 style="blue",
                                 no_wrap=True)

        # Populate the table
        for key in round:
            red, blue = key.split(', ')
            round_summary.add_row(f'{red} {EMOJI[round[key].red]}',
                                  f'{blue} {EMOJI[round[key].blue]}')

        console = Console(force_terminal=False)
        with console.capture() as capture:
            console.print(round_summary)
        send_to_everyone(capture.get())

    # Print the score
    red_score, blue_score = match.score
    send_to_everyone(f'Red: {red_score}\n'
                     f'Blue: {blue_score}')

    # Print the winner
    if red_score > blue_score:
        send_to_everyone('\nRed won!')
    elif red_score < blue_score:
        send_to_everyone('\nBlue won!')
    else:
        send_to_everyone('\nDraw :expressionless:')

    storeMatch(match)


def start_game() -> None:
    send_to_everyone('\n'
                     'Team Local Tactics!'
                     '\n'
                     'Choose a champion one player at a time.'
                     '\n')

    champions = getChamps()
    print_available_champs(champions)
    print('\n')

    player1 = []
    player2 = []

    # Champion selection
    for _ in range(2):
        input_champion(0, 'Player 1', 'red', champions, player1, player2)
        input_champion(1, 'Player 2', 'blue', champions, player2, player1)

    print('\n')

    # Match
    match = Match(
        Team([champions[name] for name in player1]),
        Team([champions[name] for name in player2])
    )
    match.play()

    # Print a summary
    print_match_summary(match)


def showHistory():
    msg = GET_HISTORY_FORM_DATABASE
    databaseSocket.send(msg)

    firstIter = True
    full = b""
    while True:
        response = databaseSocket.recv(1024)
        if firstIter:
            msgLen = int(response[:buffer])
            firstIter = False
        full += response

        if len(full) - buffer == msgLen:
            print("Got the match history")
            matchHistory = pickle.loads(full[buffer:])
            print(matchHistory)

            break

    console = Console(force_terminal=False)
    with console.capture() as capture:
        console.print(matchHistory)
    return capture.get()


connections = []

serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

serverSocket.bind(('localhost', 1200))

databaseSocket = socket(AF_INET, SOCK_STREAM)
databaseSocket.connect(('localhost', 1201))

if __name__ == '__main__':
    serverSocket.listen()
    print(databaseSocket.recv(1024))
    while True:
        (userConnection, ip) = serverSocket.accept()
        connections.append(userConnection)
        print(f"Player {len(connections)} connected")

        userConnection.send(INFO + f"Connected as player {len(connections)}".encode() + FINISHED)
        userConnection.send(INFO + f"History of games played: \n{showHistory()}".encode() + FINISHED)

        if len(connections) == 2:
            start_game()
            serverSocket.close()
            break
