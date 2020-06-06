import multiprocessing as mp
import multiprocessing.connection as mpc
import threading
import os
import sys

from dotenv import load_dotenv

# Load Env
load_dotenv()
SECRET = str.encode(os.getenv('SECRET'))

# Connect
address = ('localhost', int(sys.argv[1]))
conn = mpc.Client(address, authkey=SECRET)

def read_thread():
    while not conn.closed:
        line = conn.recv()
        print(line, end='')

reader = threading.Thread(target=read_thread)
reader.daemon = True
reader.start()

cmd = 'x'
while cmd:
    cmd = input()
    conn.send(cmd)
conn.close()
