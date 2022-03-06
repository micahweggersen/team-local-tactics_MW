from rich import print

from socket import AF_INET, SOCK_STREAM, socket

sock = socket(AF_INET, SOCK_STREAM)
sock.connect(('localhost', 1200))

while True:
    data = sock.recv(1024)
    sock.send("G".encode())
    print(data.decode('utf-8'))
