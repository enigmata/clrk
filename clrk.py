#!/usr/bin/env python3

import argparse
import pandas as pd
import sys

from collections import namedtuple
from enum import Enum
from pathlib import Path

class Verbosity(Enum):
    LOW=1
    HIGH=2

Settings=namedtuple('Settings', ['datapath','verbosity'])
InvestmentDataDetails=namedtuple('InvestmentDataDetails', ['filename','description'])

investment_data={'assets': InvestmentDataDetails(filename=Path('assets.csv'),
                                                 description='ledger of owned financial instruments'),
                 'income': InvestmentDataDetails(filename=Path('income.csv'),
                                                 description='record of income received for owned assets'),
                 'tfsa': InvestmentDataDetails(filename=Path('tfsa.csv'),
                                               description='list of TFSA allowed and actual contributions'),
                 'transactions': InvestmentDataDetails(filename=Path('transactions.csv'),
                                                       description='record of all asset transactions'),
           }

def build_cmdline_parser():
    clp_parser = argparse.ArgumentParser(description='Command-line tool for investment management')

    clp_commands = clp_parser.add_subparsers(title='Portfolio management commands',
                                             description='Execute transactions, create/print reports',
                                             dest='command')

    clp_command_list = clp_commands.add_parser('list',
                                                help='display details of investment data')
    clp_command_list.add_argument('list',
                                  choices=investment_data.keys(),
                                  help='display details of specified investment data')

    clp_command_buy = clp_commands.add_parser('buy',
                                               help='buy assets')
    clp_command_buy.add_argument('buy',
                                  action='store_true',
                                  help='buy assets')

    clp_command_datapath = clp_commands.add_parser('datapath', 
                                                    help='location of the data files')
    clp_command_datapath.add_argument('--set',
                                       type=Path,
                                       dest='path',
                                       help='directory path for the data files')

    clp_command_verbosity = clp_commands.add_parser('verbosity', 
                                                     help='level of detail printed')
    clp_command_verbosity.add_argument('--toggle',
                                        action='store_true',
                                        help='change from low to high, or vice versa')

    clp_commands.add_parser('quit', help='exit the command-line tool')

    return clp_parser

def list_data(args, settings):
    csv_file=pd.read_csv(investment_data[args.list].filename)
    print(csv_file.to_string(index=False, show_dimensions=True))

    return settings

def buy_asset(args, settings):
    print("BUY BUY BUY")
    return settings

def verbosity(args, settings):
    print(f'Current verbosity level is {settings.verbosity.name}')
    new_verbosity=settings.verbosity

    if args.toggle:
        if settings.verbosity==Verbosity.LOW:
            new_verbosity=Verbosity.HIGH
        else:
            new_verbosity=Verbosity.LOW
        print(f'New verbosity level is {new_verbosity.name}')

    return Settings(verbosity=new_verbosity,
                    datapath=settings.datapath)

def data_files_exist(path, print_output):
    csv_files_missing=False
    if path.is_dir():
        for type in investment_data:
            csv_file_path=path/investment_data[type].filename
            if csv_file_path.exists():
                if print_output:
                    print(f'  {csv_file_path} exists')
            else:
                csv_files_missing=True
                if print_output:
                    print(f'  {csv_file_path} not found')
    else:
        csv_files_missing=True
        if print_output:
            print(f'\nERROR: "{path}" is not a valid directory')

    return not csv_files_missing

def initialize_settings():
    verbosity=Verbosity.LOW
    datapath=Path('data')
    if data_files_exist(datapath, False):
        print(f'Default data path is "{datapath}"')
    else:
        valid_datapath=False
        while not valid_datapath:
            try:
                candidate_path=input('\nEnter path to data files > ')
            except EOFError:
                continue
            datapath=Path(candidate_path)
            if data_files_exist(datapath, True):
                print(f'\ndatapath is set to "{datapath}"')
                valid_datapath=True

    for type in investment_data:
        investment_data[type]=InvestmentDataDetails(filename=datapath/investment_data[type].filename,
                                                    description=investment_data[type].description)

    print(f'verbosity is set to "{verbosity.name}"\n')

    return Settings(verbosity=verbosity,
                    datapath=datapath)

def datapath(args, settings):
    print(f'Current datapath is "{settings.datapath}"')
    new_datapath=settings.datapath

    if args.path:
        if args.path.is_dir():
            print(f'\nVerifying required data files present in new dir ...')
            if data_files_exist(args.path, True):
                new_datapath=args.path
                print(f'\nNew datapath is "{new_datapath}"')
            else:
                print(f'\nERROR: not all required data files present in "{args.path}"')
                print(f'datapath remains unchanged: "{settings.datapath}"')
        else:
            print(f'\nERROR: "{args.path}" is not a valid directory')

    return Settings(verbosity=settings.verbosity,
                    datapath=Path(new_datapath))

dispatch={'buy': buy_asset,
          'datapath': datapath,
          'verbosity': verbosity,
          'list': list_data,
         }

def interactive_mode():
    print("\nInitializing ...")
    settings=initialize_settings()

    clp_parser=build_cmdline_parser()
    clp_parser.print_help()

    while True:
        try:
            cmdline=input('> ')
        except EOFError:
            break

        cmdline_tokens=cmdline.split()
        if len(cmdline_tokens)==0: continue

        try:
            args = clp_parser.parse_args(cmdline_tokens)
        except:
            args=None
        else:
            if args.command in dispatch:
                settings=dispatch[args.command](args, settings)
            elif args.command=='quit':
                break
            else:
                print("ERROR: Unrecognized command.")

if __name__=='__main__':
    interactive_mode()
    sys.exit(0)