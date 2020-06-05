import multiprocessing as mp
import multiprocessing.connection as mpc
import os
import subprocess as sp
import threading
import time

from dotenv import load_dotenv

# Load Env
load_dotenv()
SECRET = str.encode(os.getenv('SECRET'))
MCC_PORT= int(os.getenv('MCC_PORT'))

# Globals
proc = None
conn = None
address = ('localhost', MCC_PORT)

def mc_running():
    return proc and proc.poll() is None

def try_send(msg):
    try:
        conn.send(msg + '\n')
    except (OSError, AttributeError):
        print(f'TRYSEND: Failed to send: {msg}')


def mc_send(cmd):
    try:
        proc.stdin.write(str.encode(cmd + '\n'))
    except AttributeError:
        print(f'MCSEND: Server is dead')
    proc.stdin.flush()


def mc_start():
    """
    OK basically we're gonna start a minecraft process and create a listener thread dedicated to it.
    """
    global proc

    if mc_running():
        return False
    else:
        proc = sp.Popen(['java', '-Xmx1024M', '-Xms1024M', '-jar', 'server.jar', 'nogui'],
                        stdin=sp.PIPE,
                        stdout=sp.PIPE,
                        stderr=sp.STDOUT,
                        cwd='/opt/minecraft')
        # TODO verify this actually started successfully

        # Start a reader for this process
        go = threading.Event()
        def read_thread():
            line = None
            while mc_running():
                # Grab a new line if we're not holding onto a failed send
                if not line:
                    # Try reading a line. If this fails, check that the proc didn't die
                    try:
                        line = proc.stdout.readline()
                    except BrokenPipeError:
                        print('READER: Pipe read failed!')
                        continue # Top loop will handle dead process, otherwise we retry
                # Check that we have something to send
                if line:
                    # Wait for a connection to be established
                    while not conn or conn.closed:
                        time.sleep(1)
                    # Try to send the thing
                    try:
                        conn.send(f'LOG |{bytes.decode(line)}')
                        line = None
                    # If we fail, close the connection (remote probably disconnected) and leave the
                    # line so we can retry it
                    except OSError:
                        print('READER: Client disconnected!')
                        conn.close()
            print('READER: Process exited. Exiting reader thread.')

        reader = threading.Thread(target=read_thread)
        reader.daemon = True
        reader.start()

        return True


def mc_stop():
    global proc

    if not mc_running():
        return False
    else:
        mc_send('stop')
        # wait to stop
        while proc.poll() is None:
            time.sleep(1)
        proc = None
        return True

def mc_command(cmd, args):
    print(f'CMD: {cmd} {args}')
    if cmd == 'help':
        help_msg = ('ServerBot Minecraft commands:\n'
                    '!mc help - print this message\n'
                    '!mc start - start the server\n'
                    '!mc stop - stop the server\n'
                    '!mc ping - ping the server\n'
                    '!mc status - check the server status')
#                    '!mc cmd <command> - send command to the server\n'
        try_send(f'OK  |{help_msg}')
    elif cmd == 'start':
        result = mc_start()
        if result:
            try_send('OK  |Minecraft server started')
        else:
            try_send('ERR |Minecraft server is already running')
    elif cmd == 'stop':
        result = mc_stop()
        if result:
            try_send('OK  |Minecraft server stopped')
        else:
            try_send('ERR |Minecraft Server is not running')
    elif cmd == 'ping':
        try_send(f'OK  |pong')
    elif cmd == 'status':
        if mc_running():
            try_send('OK  |Minecraft Server is running')
        else:
            try_send('OK  |Minecraft Server is not running')
#    elif cmd == 'cmd':
#        if proc:
#            mc_send(args)
#            try_send('OK  |')
#        else:
#            try_send('ERR |Minecraft Server is not running')
    else:
        try_send(f'ERR |Unknown command: {cmd}')


# Open IPC channel
listener = mpc.Listener(address, authkey=SECRET)

# Wait for connections
while True:
    try:
        conn = listener.accept()
    except (EOFError, ConnectionResetError, BrokenPipeError):
        print('LISTENER: Failed to connect to client')
        continue
    print('LISTENER: Client connected!')
    while conn and (not conn.closed):
        try:
            line = conn.recv()
            tokens = line.split(' ', 1)
            cmd = tokens[0]
            args = None
            if len(tokens) > 1:
                args = tokens[1].rstrip()
            mc_command(cmd, args)
        except (EOFError, ConnectionResetError, BrokenPipeError):
            print(f'LISTENER: Client disconnected!')
            conn.close()

# TODO: detect crash and alert back to discord
