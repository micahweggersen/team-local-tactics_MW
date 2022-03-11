import os
import pickle
from socket import AF_INET, SO_REUSEADDR, SOCK_STREAM, socket
from ssl import SOL_SOCKET

import pymongo
from pymongo.server_api import ServerApi
from rich.table import Table

from enumValues import FINISHED, INPUT, INFO, GET_HISTORY_FORM_DATABASE, SEND_HISTORY_TO_DATABASE, GET_CHAMPTIONS

from champlistloader import load_some_champs

databaseSocket = socket(AF_INET, SOCK_STREAM)
databaseSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
databaseSocket.bind(('localhost', 1201))

buffer = 10

password = os.environ.get("password")
client = pymongo.MongoClient(
    "mongodb+srv://root:12345@cluster0.nvomw.mongodb.net/myFirstDatabase?retryWrites=true&w=majority",
    server_api=ServerApi('1'))

database = client.INF142
Champions = database.Champions
MatchHistory = database.history

for champion in list(load_some_champs().values()):
    db_count = list(Champions.find({"name": champion.name}))
    if len(db_count) == 0:
        print("legger til")
        championsDocument = {
            "name": champion.name,
            "ROCK": champion._rock,
            "Paper": champion._paper,
            "Scissors": champion._scissors
        }
        Champions.insert_one(championsDocument)


def get_champ_list():
    load_some_champs()
    data = []
    for champion in list(load_some_champs().values()):
        championsDocument = {
            "name": champion.name,
            "ROCK": champion._rock,
            "Paper": champion._paper,
            "Scissors": champion._scissors
        }
        data.append(championsDocument)
    return load_some_champs()


def set_game_history(history):
    match = {
        "red": history.score[0],
        "blue": history.score[1],
        "red_champ_one": history.red_team.champions[0].name,
        "red_champ_two": history.red_team.champions[1].name,
        "blue_champ_one": history.blue_team.champions[0].name,
        "blue_champ_two": history.blue_team.champions[1].name
    }
    MatchHistory.insert_one(match)


def get_latest_match():
    history = MatchHistory.find()
    m = Table(title="Match History")
    m.add_column("ID")
    m.add_column("RED CHAMPION ONE")
    m.add_column("RED CHAMPION TWO")
    m.add_column("Red")
    m.add_column("BLUE CHAMPION ONE")
    m.add_column("BLUE CHAMPION TWO")
    m.add_column("Blue")

    for rec in history:
        m.add_row(str(rec['_id']), str(rec['red_champ_one']), str(rec['red_champ_two']), str(rec['red']),
                  str(rec['blue_champ_one']), str(rec['blue_champ_two']), str(rec['blue']))
    return m


while True:
    databaseSocket.listen()
    (userConnection, ip) = databaseSocket.accept()
    userConnection.send(INFO + "Database connected!".encode() + FINISHED)
    message = bytes()
    while True:
        data = userConnection.recv(1024)

        if data == GET_CHAMPTIONS:
            champs = get_champ_list()
            msg = pickle.dumps(champs)
            msg = bytes(f"{len(msg):<{buffer}}", "utf-8") + msg
            userConnection.send(msg)
        elif data == SEND_HISTORY_TO_DATABASE:
            firstIter = True
            full = b""
            while True:
                response = userConnection.recv(1024)
                if firstIter:
                    msgLen = int(response[:buffer])
                    firstIter = False
                full += response

                if len(full) - buffer == msgLen:
                    history = pickle.loads(full[buffer:])
                    set_game_history(history)
                    print("Saved")
                    break
            break
        elif data == GET_HISTORY_FORM_DATABASE:
            match = get_latest_match()
            msg = pickle.dumps(match)
            msg = bytes(f"{len(msg):<{buffer}}", "utf-8") + msg
            userConnection.send(msg)
            print("sent match history")
