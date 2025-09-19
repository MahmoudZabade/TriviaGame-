import socket
import threading
import time
import os
import random
from setup import (
    MESSAGE_STATUSES,
    QUESTIONS,
    MIN_PLAYERS,
    GAME_START_DELAY,
    GAME_QUESTION_DELAY,
    NUMBER_OF_ROUNDS,
    NUMBER_OF_QUESTIONS_PER_ROUND,
    DELAY_BETWEEN_QUESTIONS,
    WAITING_FOR_PLAYERS_DELAY,
)

from client import Client

clients_answers = {}
questions = []
answer = ""


class Server:
    def __init__(self):
        self.host = socket.gethostbyname(socket.gethostname())
        self.port = 5689
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind((self.host, self.port))
        self.clients = {}

    def broadcast(self, msg, exclude=None):
        for addr, client in self.clients.items():
            if addr != exclude:
                self.s.sendto(msg.encode(), addr)

    def send(self, msg, addr):
        self.s.sendto(msg.encode(), addr)

    def receive(self):
        while True:
            try:
                data, addr = self.s.recvfrom(1024)
                data = data.decode()
                status = data.split(":")[0]
                msg = data.split(":")[1]
                if status == MESSAGE_STATUSES["join"]:
                    client = Client(self.host, self.port, msg, addr)
                    self.clients[addr] = client
                    print(f"{client.name} has joined the game.")
                    print(f"Total players: {len(self.clients)}")
                    self.s.sendto(
                        f"{MESSAGE_STATUSES['join']}:Welcome to the game!".encode(),
                        addr,
                    )
                    self.broadcast(
                        f"{MESSAGE_STATUSES['join']}:{msg} has joined the game.",
                        exclude=addr,
                    )
                elif status == MESSAGE_STATUSES["quit"]:
                    client: Client = self.clients.pop(addr)
                    print(f"{client.name} has left the game.")
                    self.broadcast(
                        f"{MESSAGE_STATUSES['left']}:{client.name} has left the game."
                    )
                elif status == MESSAGE_STATUSES["message"]:
                    print(f"{self.clients[addr].name}: {msg}")
                elif status == MESSAGE_STATUSES["answer"]:
                    global answer
                    clients_answers[self.clients[addr].name] = (msg, time.time())
                    self.clients[addr].offline_counter = 0
                    print(f"{self.clients[addr].name} answered: {msg}")
            except Exception as e:
                print(f"Error receiving data: {e}")
                pass

    def game(self):
        global clients_answers, questions, answer
        while True:
            if len(self.clients) >= MIN_PLAYERS:
                self.broadcast(
                    f"{MESSAGE_STATUSES['start']}:Starting game... in {GAME_START_DELAY} seconds."
                )
                time.sleep(GAME_START_DELAY)
                self.broadcast(f"{MESSAGE_STATUSES['info']}:Game started!")

                for round in range(NUMBER_OF_ROUNDS):
                    # Reset scores at the start of each round
                    for client in self.clients.values():
                        client.score = 0

                    self.broadcast(
                        f"{MESSAGE_STATUSES['info']}:Round {round + 1} of {NUMBER_OF_ROUNDS}"
                    )
                    questions = random.sample(
                        list(QUESTIONS.keys()), NUMBER_OF_QUESTIONS_PER_ROUND
                    )
                    for i, question in enumerate(questions):
                        if len(self.clients) < MIN_PLAYERS:
                            break
                        answer = str(QUESTIONS[question])
                        print(f"Question {i + 1}: {question}")
                        print(f"Answer: {answer}")
                        self.broadcast(f"{MESSAGE_STATUSES['question']}:{question}")
                        time.sleep(GAME_QUESTION_DELAY)
                        self.broadcast(
                            f"{MESSAGE_STATUSES['info']}:Time's up! The answer is {answer}"
                        )

                        for addr, client in list(self.clients.items()):
                            if client.name not in clients_answers:
                                client.offline_counter += 1
                                print(f"{client.name} did not answer.")
                                if client.offline_counter >= 3:
                                    print(f"{client.name} has been kicked.")
                                    self.broadcast(
                                        f"{MESSAGE_STATUSES['info']}:{client.name} has been kicked.",
                                        exclude=addr,
                                    )
                                    self.clients.pop(addr)
                                    self.send(
                                        f"{MESSAGE_STATUSES['kicked']}:You have been kicked.",
                                        addr,
                                    )
                        correct_answers = [
                            (name, timestamp)
                            for name, (response, timestamp) in clients_answers.items()
                            if response == answer
                        ]

                        correct_answers.sort(key=lambda x: x[1])  # Sort by time

                        # Dynamically assign scores based on the number of correct answers
                        num_correct = len(correct_answers)
                        for idx, (name, _) in enumerate(correct_answers):
                            score_increment = (num_correct - idx) / num_correct
                            client = [
                                c
                                for addr, c in self.clients.items()
                                if c.name == name
                            ][0]
                            client.score += score_increment

                        clients_answers.clear()

                        # Update leaderboard
                        leaderboard = "\033[1mLeaderboard\033[0m\n"
                        for client in sorted(
                            self.clients.values(), key=lambda x: x.score, reverse=True
                        ):
                            leaderboard += f"{client.name} - {client.score:.2f}\n"

                        print(leaderboard)
                        self.broadcast(f"{MESSAGE_STATUSES['score']}:{leaderboard}")
                        time.sleep(DELAY_BETWEEN_QUESTIONS)

                    if len(self.clients) < MIN_PLAYERS:
                        break

                    self.broadcast(f"{MESSAGE_STATUSES['info']}:Round ended.")
                    winner = max(self.clients.values(), key=lambda x: x.score)
                    self.broadcast(
                        f"{MESSAGE_STATUSES['winner']}:Round winner is {winner.name} with {winner.score:.2f} points!"
                    )
                    for client in self.clients.values():
                        client.total_wins += 1 if client == winner else 0

                    if round == NUMBER_OF_ROUNDS - 1:
                        print("Game ended.")
                        self.broadcast(f"{MESSAGE_STATUSES['info']}:Game ended.")
                        final_winner = max(
                            self.clients.values(), key=lambda x: x.total_wins
                        )
                        self.broadcast(
                            f"{MESSAGE_STATUSES['winner']}:{final_winner.name} is the final winner!"
                        )

            else:
                print("Waiting for players...")
                time.sleep(WAITING_FOR_PLAYERS_DELAY)


def main():
    server = Server()
    print(f"Server started at {server.host}")
    threading.Thread(target=server.receive).start()
    threading.Thread(target=server.game).start()
    while True:
        pass
    os._exit(0)


if __name__ == "__main__":
    main()
