from socket import AF_INET, SOCK_STREAM, socket
from rich import print
from rich.prompt import Prompt
from rich.table import Table

from enumValues import FINISHED, INPUT, INFO


def send_input(prompt):
    msg = input(prompt)
    sock.send(msg.encode())


def prompt_user(prompt):
    answer = Prompt.ask(prompt);
    sock.send(answer.encode())


sock = socket(AF_INET, SOCK_STREAM)

sock.connect(('localhost', 1200))

while True:
    data = sock.recv(1024)
    if not data:
        break

    do_print = False
    need_input = False

    message = bytes()
    for b in [data[i:i + 1] for i in range(len(data))]:
        if b == INFO:
            do_print = True
        if b == FINISHED:
            if need_input:
                prompt_user(message.decode())
            else:
                print(message.decode())

            do_print = False
            need_input = False
            message = bytes()
        if b == INPUT:
            need_input = True
            do_print = True
        if do_print:
            message += b
