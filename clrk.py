#!/usr/bin/env python3

import argparse
import sys

def build_cmdline_parser():
    clp_parser = argparse.ArgumentParser(description='Command-line tool for investment management')

    clp_parser.add_argument('--verbose',
                             action='store_true',
                             help='print additional details')

    clp_commands = clp_parser.add_subparsers(title='Portfolio management commands',
                                             description='Execute transactions, create/print reports',
                                             dest='command')

    clp_command_buy = clp_commands.add_parser('buy',
                                               help='buy assets')

    clp_command_buy.add_argument('buy',
                                  action='store_true',
                                  help='buy assets')

    clp_commands.add_parser('quit', help='exit the command-line tool')

    return clp_parser

def interactive_mode():
    clp_parser = build_cmdline_parser()

    clp_parser.print_help()

    while True:
        try:
            cmdline = input('> ')
        except EOFError:
            break

        cmdline_tokens = cmdline.split()
        if len(cmdline_tokens) == 0: continue

        try:
            args = clp_parser.parse_args(cmdline_tokens)
        except:
            args = None
        else:
            print(args)
            if args.command=='quit':
                break
            elif args.command=='buy':
                print("BUY BUY BUY")
            else:
                print("ERROR: Unrecognized command.")

if __name__ == '__main__':

    interactive_mode()

    sys.exit(0)
