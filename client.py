import socket
import threading
import time
import sys
import os
import asyncio
import aioconsole
from setup import MESSAGE_STATUSES, GAME_QUESTION_DELAY


class Client:
    def __init__(self, server_addr, server_port, name, addr=None):
        self.server_addr = server_addr
        self.server_port = server_port
        self.s = None
        self.addr = addr
        self.name = name
        self.offline_counter = 0
        self.score = 0
        self.total_wins = 0

    def send(self, msg):
        self.s.sendto(msg.encode(), (self.server_addr, self.server_port))

    async def send_answer(self):
        try:
            answer = await asyncio.wait_for(
                aioconsole.ainput("Enter your answer or 'quit' to exit: "),
                timeout=GAME_QUESTION_DELAY,
            )
            if answer.lower() == "quit":
                self.send(f"{MESSAGE_STATUSES['quit']}:{self.name}")
                self.s.close()
                os._exit(0)
            self.send(f"{MESSAGE_STATUSES['answer']}:{answer}")
        except asyncio.TimeoutError:
            print("Time's up! No answer received.")

    def receive(self):
        while True:
            try:
                data, addr = self.s.recvfrom(1024)
                data = data.decode()
                status = data.split(":")[0]
                msg = data.split(":")[1]
                if status == MESSAGE_STATUSES["join"]:
                    print(msg)
                elif status == MESSAGE_STATUSES["left"]:
                    print(msg)
                elif status == MESSAGE_STATUSES["kicked"]:
                    print(msg)
                    os._exit(0)
                elif status == MESSAGE_STATUSES["start"]:
                    print(msg)
                elif status == MESSAGE_STATUSES["info"]:
                    print(msg)
                elif status == MESSAGE_STATUSES["question"]:
                    print(msg)
                    asyncio.run(self.send_answer())

                elif status == MESSAGE_STATUSES["score"]:
                    print(msg)
                elif status == MESSAGE_STATUSES["winner"]:
                    print(msg)
                elif status == MESSAGE_STATUSES["error"]:
                    print(msg)
                    os._exit(0)

            except Exception as e:
                print(f"Error receiving data: {e}")
                pass

    def start(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send(f"{MESSAGE_STATUSES['join']}:{self.name}")


async def main():
    server_addr = input("Enter server address: ")
    server_port = int(input("Enter server port: "))
    name = input("Enter your name: ")
    client = Client(server_addr, server_port, name)
    client.start()

    # Run the receive method inside a thread to handle socket communication
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, client.receive)

    # Keep the event loop running to allow async functions to work
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())



