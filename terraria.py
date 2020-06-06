import asyncio
import multiprocessing as mp
import multiprocessing.connection as mpc
import os
import subprocess as sp
import threading
import time
import dotenv as de

__all__ = ['Terraria']

# Load Env
de.load_dotenv()
SECRET = str.encode(os.getenv('SECRET'))
BOT_CHAN_ID = int(os.getenv('BOT_CHAN_ID'))
TE_LOG_CHAN_ID = int(os.getenv('TE_LOG_CHAN_ID'))
TE_DIR = os.getenv('TE_DIR')
TEC_PORT = int(os.getenv('TEC_PORT'))
TE_PREFIX = os.getenv('TE_PREFIX')

# Globals (for controller)
proc = None
conn = None


class Terraria:
    """
    Class for importing by the serverbot. It will handle all communication with the Terraria
    Controller (the functionality implemented by the rest of this module.

    Just initialize it and register the send function for callback with the prefix
    """

    def __init__(self,
                 client,
                 guild,
                 prefix=TE_PREFIX,
                 port=TEC_PORT,
                 botchanid=BOT_CHAN_ID,
                 logchanid=TE_LOG_CHAN_ID
                 ):
        """
        Initializes a new Terraria object for communicating with a Terraria Controller.

        Args:
            client:    The Discord client to interact with
            guild:     The Discord server (guild) the bot should respond on
            prefix:    (Optional) The Discord server prefix. Defaults to env var
            port:      (Optional) The port to run the Terraria controller on. Defaults to
                       environment variable
            botchanid: (Optional) The id of the Discord server bot channel. Defaults to environment
                       variable
            logchanid: (Optional) The id of the Discord server Terraria log channel. Defaults to
                       environment variable

        Returns:
            A newly initialized Terraria object
        """

        # Set up members
        self.prefix = prefix
        self.port = port
        self.guild = guild
        self.client = client
        self.logchan = guild.get_channel(logchanid)
        self.botchan = guild.get_channel(botchanid)
        self.__conn = None

        def read_thread():
            """
            Launch the read thread. This will attempt to create a connection to a te server
            controller and listen for incoming data. This thread will stay alive until the process
            closes.
            """

            while True:

                # First connect to the server
                try:
                    self.__conn = mpc.Client(('localhost', port), authkey=SECRET)
                    self.__botchan_send('Terraria server manager connected!')

                # Leaving unassigned or closing skips the next loop
                except (EOFError, ConnectionRefusedError, ConnectionResetError, BrokenPipeError):
                    if self.__conn is not None:
                        self.__conn.close()
                        time.sleep(10) # Wait a reasonable amount of time and chek again

                # Read loop
                while self.__conn and (not self.__conn.closed):

                    # Try to read and direct messages appropriately
                    try:
                        line = self.__conn.recv()
                        [status, msg] = line.split('|', 1)
                        status = status.strip()
                        if status == 'LOG':
                            self.__logchan_send(msg)
                        elif status == 'OK':
                            self.__botchan_send(msg)
                        else:
                            self.__botchan_send(f'{status}: {msg}')

                    # Close the connection so we end the loop and try to reconnect at the top
                    except (EOFError, ConnectionResetError, BrokenPipeError):
                        self.__botchan_send('ERR: The Terraria server manager crashed. Attempting '
                                            'to reconnect')
                        self.__conn.close()

        # Start a daemon reader thread
        reader = threading.Thread(target=read_thread)
        reader.daemon = True
        reader.start()


    def try_send(self, msg):
        """
        Try to send a message to the controller. If we fail, print an error to the bot channel. We
        don't need to handle the failure here since the reader reads in a tight loop so a connection
        failure will be caught there as well and will trigger a reconnect.

        Args:
            msg: The message to try to send
        """

        try:
            self.__conn.send(msg)
        except (OSError, AttributeError):
            # We lost connection. We'll just log it and let the read loop handle reconnecting
            self.__botchan_send('Could not send command to Terraria server manager')


    def __logchan_send(self, msg):
        """
        Send a message to the log channel.

        Args:
            msg: The message to send
        """

        asyncio.run_coroutine_threadsafe(self.logchan.send(msg), self.client.loop)


    def __botchan_send(self, msg):
        """
        Send a message to the bot channel.

        Args:
            msg: The message to send
        """

        asyncio.run_coroutine_threadsafe(self.botchan.send(msg), self.client.loop)



def te_running():
    """
    Check if the Terraria server process is running.

    Returns:
        True if the server process is running, False otherwise
    """

    return proc and proc.poll() is None


def try_send(msg):
    """
    Try to send a message to the connected client (usually serverbot). We don't need to handle the
    failure here since the reader reads in a tight loop so a connection failure will be caught there
    as well and will trigger a reconnect. We also can't send an error message since the client isn't
    connected to receive the message so we'll just fail silently.

    Args:
        msg: The message to try to send
    """

    try:
        conn.send(msg + '\n')
    except (OSError, AttributeError):
        # Since we lost connection to the client we can't really notify them there's an issues so
        # just log it and fail
        print(f'try_send: Failed to send: {msg}')


def te_writeline(cmd):
    """
    Try to send a message to the Terraria process. We don't need to hand the failure here since the
    reader will catch it and mark the server dead.

    Args:
        cmd: The Terraria command to send

    Returns:
        True if successful, False otherwise
    """

    try:
        proc.stdin.write(str.encode(f'{cmd}\n'))
        proc.stdin.flush()
        return True
    except AttributeError:
        print(f'te_writeline: Server is dead')
        return False


def te_start():
    """
    Start a new Terraria process and spin up a listener thread to handle incoming data.

    Returns:
        True if the server was started successfully, False otherwise (e.g. if server is already
        running)
    """

    global proc

    # Fastfail if the server is running, else start it
    if te_running():
        return False
    else:
        proc = sp.Popen(['bash', 'TerrariaServer', '-config', 'serverconfig.txt'],
                        stdin=sp.PIPE,
                        stdout=sp.PIPE,
                        stderr=sp.STDOUT,
                        cwd=TE_DIR)

        # TODO verify this actually started successfully

        # Start a reader for this process
        def read_thread():
            """
            Launch the reader thread. This will attempt to read from the Terraria process and send
            it to the client (serverbot) to process. If a send fails, it will keep retrying until it
            succeeds. If a read fails, we continue and the top loop will catch the dead proces and
            report it to the client (serverbot)
            """

            line = None
            while te_running():

                # Grab a new line if we're not holding onto a failed send
                if not line:

                    # Try reading a line. If this fails, check that the proc didn't die
                    try:
                        line = proc.stdout.readline()
                    except BrokenPipeError:
                        print('reader: Pipe read failed!')
                        continue # Top loop will handle dead process, otherwise we retry

                # Check that we have something to send
                if line:

                    # Wait for a connection to be established
                    while not conn or conn.closed:
                        time.sleep(10) # wait for the connection to come back up

                    # Try to send the thing
                    try:
                        conn.send(f'LOG |{bytes.decode(line)}')
                        line = None

                    # If we fail, close the connection (remote probably disconnected) and leave the
                    # line so we can retry it
                    except OSError:
                        print('reader: Client disconnected!')
                        conn.close()

            print('reader: Process exited. Exiting reader thread.')

        # Start up the reader thread
        reader = threading.Thread(target=read_thread)
        reader.daemon = True
        reader.start()

        return True


def te_stop():
    """
    Cleanly save and stop the currently running Terraria server, if any

    Returns:
        True if successful, False otherwise (e.g. if server isn't running)
    """

    global proc

    if not te_running():
        return False
    else:
        te_writeline('exit')
        # wait to stop
        while proc.poll() is None:
            time.sleep(1)
        proc = None
        return True


def te_command(cmd, args):
    """
    Interpret a command given by the client (serverbot) and execute the appropriate action

    Args:
        cmd:  The command to run
        args: (Optional) Any optional arguments to the command
    """

    # Remove newlines to prevent command injection
    if args is not None:
        args.replace('\n','')

    print(f'te_command: {cmd} {args}')

    help_msg = ('ServerBot Terraria commands:\n'
                f'!{TE_PREFIX} help - print this message\n'
                f'!{TE_PREFIX} ping - ping the server\n'
                f'!{TE_PREFIX} status - check the server status\n'
                f'!{TE_PREFIX} start - start the server\n'
                f'!{TE_PREFIX} stop - stop the server')

    # Print help message
    if cmd == 'help':
        try_send(f'OK  |{help_msg}')

    # Start the server
    elif cmd == 'start':
        result = te_start()
        if result:
            try_send('OK  |Terraria server starting')
        else:
            try_send('ERR |Terraria server is already running')

    # Stop the server
    elif cmd == 'stop':
        result = te_stop()
        if result:
            try_send('OK  |Terraria server stopped')
        else:
            try_send('ERR |Terraria Server is not running')

    # Ping
    elif cmd == 'ping':
        try_send(f'OK  |pong')

    # Print the server status
    elif cmd == 'status':
        if te_running():
            try_send('OK  |Terraria Server is running')
        else:
            try_send('OK  |Terraria Server is not running')

    # We didn't get a valid command
    else:
        try_send(f'ERR |Unknown command: {cmd}')
        try_send(f'OK  |{help_msg}')


# Main
if __name__ == '__main__':

    # Open IPC channel
    listener = mpc.Listener(('localhost', TEC_PORT), authkey=SECRET)

    while True:

        # Wait until we connect to a client (serverbot)
        try:
            conn = listener.accept()
        except (EOFError, ConnectionResetError, BrokenPipeError):
            print('main: Failed to connect to client')
            continue
        print('main: Client connected!')

        # If connection succeeded, listen for incoming commands
        while conn and (not conn.closed):

            # Try the receive a command and execute it. If there's a failure, we assume the
            # conneciton failed and close it (in order to reopen it)
            try:
                line = conn.recv()
                tokens = line.split(None, 1)
                cmd = tokens[0]
                args = None
                if len(tokens) > 1:
                    args = tokens[1].rstrip()
                te_command(cmd, args)
            except (EOFError, ConnectionResetError, BrokenPipeError):
                print(f'main: Client disconnected!')
                conn.close()
