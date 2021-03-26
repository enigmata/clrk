#!/usr/bin/env python3

import argparse
import pandas as pd
import sys

from collections import namedtuple
from datetime import date
from enum import Enum
from pathlib import Path

class Verbosity(Enum):
    LOW=1
    HIGH=2

Settings=namedtuple('Settings', ['datapath','verbosity'])
InvestmentDataDetails=namedtuple('InvestmentDataDetails', ['filename','columns','description'])
AccountTypes=['sdrsp','locked_sdrsp','margin','tfsa','resp']
TransactionTypes=['buy','sell']

investment_data={'assets': InvestmentDataDetails(filename=Path('assets.csv'),
                                                 columns=['name','market','type','subtype','income_per_unit_period','sdrsp','locked_sdrsp','margin','tfsa','resp','income_freq_months','income_first_month','income_day_of_month'],
                                                 description='ledger of owned financial instruments'),
                 'income': InvestmentDataDetails(filename=Path('income.csv'),
                                                 columns=['name','date','account','units','income'],
                                                 description='record of income received for owned assets'),
                 'tfsa': InvestmentDataDetails(filename=Path('tfsa.csv'),
                                               columns=['year','contributed','max_contribution'],
                                               description='list of TFSA allowed and actual contributions'),
                 'transactions': InvestmentDataDetails(filename=Path('transactions.csv'),
                                                       columns=['date','type','name','account','units','unit_price','fees','total_cost'],
                                                       description='record of all asset transactions'),
}

def build_cmdline_parser():
    clp_parser = argparse.ArgumentParser(prog='',
                                         description='Command-line tool for investment management',
                                         add_help=False)

    clp_commands = clp_parser.add_subparsers(title='Portfolio management commands',
                                             description='Execute transactions, create/print reports',
                                             dest='command')

    clp_command_list = clp_commands.add_parser('list',
                                                help='display details of investment data')
    clp_command_list.add_argument('list',
                                  choices=investment_data.keys(),
                                  help='display details of specified investment data')
    clp_command_list.add_argument('--filter',
                                  help="e.g. ((df['name']=='TD')|(df['name']=='ENB'))&(~(df['account']=='margin'))")

    clp_command_buy = clp_commands.add_parser('transact',
                                               help='buy or sell assets')
    clp_command_buy.add_argument('type',
                                  choices=TransactionTypes,
                                  help='type of transaction: buy or sell')
    clp_command_buy.add_argument('account',
                                  choices=AccountTypes,
                                  help='account in which transaction was executed')
    clp_command_buy.add_argument('name',
                                  help='name of asset being transacted')
    clp_command_buy.add_argument('units',
                                  type=int,
                                  help='number of units bought or sold')
    clp_command_buy.add_argument('price',
                                  type=float,
                                  help='price of units bought or sold (e.g. "9.99")')
    clp_command_buy.add_argument('--date',
                                  type=date.fromisoformat,
                                  default=date.today(),
                                  help='transaction date (e.g. "2021-03-31")')
    clp_command_buy.add_argument('--fees',
                                  type=float,
                                  default=9.99,
                                  help='total transaction fees (e.g. "9.99")')

    clp_command_income = clp_commands.add_parser('income',
                                               help='add income payments')
    clp_command_income.add_argument('name',
                                  help='name of asset for which income is received')
    clp_command_income.add_argument('account',
                                  choices=AccountTypes,
                                  help='account in which income was deposited')
    clp_command_income.add_argument('units',
                                  type=int,
                                  help='number of units of income paid')
    clp_command_income.add_argument('income',
                                  type=float,
                                  help='total income received')
    clp_command_income.add_argument('--date',
                                  type=date.fromisoformat,
                                  default=date.today(),
                                  help='date income received (e.g. "2021-03-31")')

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

    clp_commands.add_parser('help', help='print help overview')
    clp_commands.add_parser('quit', help='exit the command-line tool')

    return clp_parser

def list_data(args, settings):
    df=pd.read_csv(investment_data[args.list].filename)
    if args.filter:
        filter=eval(args.filter)
        df=df[filter]
    print(df.to_string(index=False, show_dimensions=True))
    return settings

def append_csv(data_type, df_to_append):
    print(f'\n{data_type} data to append:\n')
    print(df_to_append.to_string(index=False, show_dimensions=True))
    csv_file_df=pd.read_csv(investment_data[data_type].filename)
    combined_df=pd.concat([csv_file_df, df_to_append])
    print(f'\n{data_type} data appended and written to file:\n')
    print(combined_df.to_string(index=False, show_dimensions=True),'\n')
    combined_df.to_csv(investment_data[data_type].filename, index=False)

def buy_sell_asset(args, settings):
    investment_data_type='transactions'
    total_cost=round((args.units*args.price)+args.fees,2)
    df=pd.DataFrame([[args.date.strftime("%Y-%m-%d"),args.type,args.name,args.account,args.units,round(args.price,2),round(args.fees,2),total_cost]],
                    columns=investment_data[investment_data_type].columns)
    append_csv(investment_data_type, df)
    return settings

def income_received(args, settings):
    investment_data_type='income'
    df=pd.DataFrame([[args.name,args.date.strftime("%Y-%m-%d"),args.account,args.units,round(args.income,2)]],
                    columns=investment_data[investment_data_type].columns)
    append_csv(investment_data_type, df)
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
                                                    columns=investment_data[type].columns,
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

dispatch={'transact': buy_sell_asset,
          'datapath': datapath,
          'verbosity': verbosity,
          'list': list_data,
          'income': income_received,
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
            elif args.command=='help':
                clp_parser.print_help()
            elif args.command=='quit':
                break
            else:
                print("ERROR: Unrecognized command.")

if __name__=='__main__':
    interactive_mode()
    sys.exit(0)