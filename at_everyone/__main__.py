import argparse; from argparse import ArgumentParser
from .parser import parse
from .interpreter import evaluate
from . import DeadChat
import at_everyone.options as options
import asyncio
import sys
# from http.client import HTTPConnection
  
# def check_internet_connection(url="www.google.com", timeout=30):
#     connection = HTTPConnection(url, timeout=timeout)
#     try:
#         # only header requested for fast operation
#         connection.request("HEAD", "/")
#         return True
#     except Exception:
#         return False
#     finally:
#         connection.close()

import socket

def check_internet_connection():
    """ Returns True if there's a connection """

    IP_ADDRESS_LIST = [
        "1.1.1.1",  # Cloudflare
        "1.0.0.1",
        "8.8.8.8",  # Google DNS
        "8.8.4.4",
        "208.67.222.222",  # Open DNS
        "208.67.220.220"
    ]

    port = 53
    socket.setdefaulttimeout(3)
    for host in IP_ADDRESS_LIST:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            s.close()
            return True
        except socket.error:
            pass
    return False

parser = ArgumentParser()
parser.add_argument('file', type=argparse.FileType('r'))
parser.add_argument('--require-uppercase-variables', action=argparse.BooleanOptionalAction, default=options.require_uppercase_variable_names)
parser.add_argument('--require-uppercase-labels', action=argparse.BooleanOptionalAction, default=options.require_uppercase_label_names)
parser.add_argument('--unsafe-variable-names', action=argparse.BooleanOptionalAction, default=options.allow_unsafe_variable_names)
parser.add_argument('--lenient-syntax', action=argparse.BooleanOptionalAction, default=options.lenient_syntax)
parser.add_argument('--language-extensions', action=argparse.BooleanOptionalAction, default=options.language_extensions)
parser.add_argument('--bounded-integers', action=argparse.BooleanOptionalAction, default=options.bounded_integers)
# parser.add_argument('--internet-check-url', default='www.google.com')
args = parser.parse_args()
options.require_uppercase_variable_names = args.require_uppercase_variables
options.require_uppercase_label_names = args.require_uppercase_labels
options.allow_unsafe_variable_names = args.unsafe_variable_names
options.lenient_syntax = args.lenient_syntax
options.language_extensions = args.language_extensions
with args.file:
    stmts = parse(args.file)
# evaluate(stmts)

if not check_internet_connection():
    sys.stderr.write("Your message could not be sent.\n")
    sys.exit(1)

exit_status = 0

async def eval_stmts():
    global exit_status
    try:
        evaluate(stmts)
    except DeadChat as e:
        print(e.args[0] if e.args and isinstance(e.args[0], str) else "Dead chat.", file=sys.stderr)
        exit_status = 1
    except KeyboardInterrupt:
        exit_status = 1
        raise
    finally:
        exit_task.cancel()

async def exit_after_1min():
    global exit_status
    await asyncio.sleep(60)
    print("Everyone has died of boredom.", file=sys.stderr)
    exit_status = 1
    main_task.cancel()

main_task: asyncio.Task
exit_task: asyncio.Task

async def run():
    global main_task, exit_task
    main_task = asyncio.create_task(eval_stmts())
    exit_task = asyncio.create_task(exit_after_1min())

event_loop = asyncio.new_event_loop()
asyncio.set_event_loop(event_loop)
try:
    event_loop.run_until_complete(run())
finally:
    event_loop.run_until_complete(event_loop.shutdown_asyncgens())
    event_loop.close()
sys.exit(exit_status)