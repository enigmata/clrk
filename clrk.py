#!/usr/bin/env python3

import argparse
import pandas as pd
import sys

from collections import namedtuple
from datetime import date
from enum import Enum
from pathlib import Path
from time import localtime, strftime

class Verbosity(Enum):
    LOW=1
    HIGH=2

Settings=namedtuple('Settings', ['datapath','verbosity'])
InvestmentDataDetails=namedtuple('InvestmentDataDetails', ['filename','columns','description'])
AccountTypes=['sdrsp','locked_sdrsp','margin','tfsa','resp']
ReportTypes=['monthly_income','tfsa_summary']
ReportFormats=['csv']
TransactionTypes=['buy','sell','xfer','cont','cont_limit']

investment_data={'assets': InvestmentDataDetails(filename=Path('assets.csv'),
                                                 columns=['name','market','type','subtype','income_per_unit_period','sdrsp','locked_sdrsp','margin','tfsa','resp','income_freq_months','income_first_month','income_day_of_month'],
                                                 description='ledger of owned financial instruments'),
                 'income': InvestmentDataDetails(filename=Path('income.csv'),
                                                 columns=['name','date','account','units','income'],
                                                 description='record of income received for owned assets'),
                 'monthly_income': InvestmentDataDetails(filename=Path('income_monthly.csv'),
                                                         columns=['name','sdrsp','locked_sdrsp','margin','tfsa','resp','total_rrsp','total_nonrrsp','monthly_total','yearly_total'],
                                                         description='monthly income by account, including overall & RRSP and non-registered totals'),
                 'tfsa_summary': InvestmentDataDetails(filename=Path('tfsa_summary.csv'),
                                                       columns=['num_transactions','total'],
                                                       description='summarization of tfsa transactions'),
                 'transactions': InvestmentDataDetails(filename=Path('transactions.csv'),
                                                       columns=['date','type','name','account','xfer_account','units','unit_amount','fees','total'],
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

    clp_command_transact = clp_commands.add_parser('transact',
                                                   help='perform a transaction on an asset')
    clp_command_transact.add_argument('type',
                                      choices=TransactionTypes,
                                      help='type of transaction')
    clp_command_transact.add_argument('account',
                                      choices=AccountTypes,
                                      help='account in which transaction was executed')
    clp_command_transact.add_argument('--xfer_account',
                                      choices=AccountTypes,
                                      help='the target account of a xfer transaction')
    clp_command_transact.add_argument('name',
                                      help='name of asset being transacted, or "cash"')
    clp_command_transact.add_argument('units',
                                      type=int,
                                      help='number of units participating in transaction')
    clp_command_transact.add_argument('amount',
                                      type=float,
                                      help='cost of a stock unit or contribution amount per unit')
    clp_command_transact.add_argument('--date',
                                      type=date.fromisoformat,
                                      default=date.today(),
                                      help='transaction date (e.g. "2021-03-31")')
    clp_command_transact.add_argument('--fees',
                                      type=float,
                                      default=0.00,
                                      help='total transaction fees (default: "0.00")')

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

    clp_command_report = clp_commands.add_parser('report',
                                                  help='generate a report on investment data')
    clp_command_report.add_argument('type',
                                     choices=ReportTypes,
                                     help='type of report to generate')
    clp_command_report.add_argument('format',
                                     choices=ReportFormats,
                                     help='how to format the report')

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

def generate_report(args, settings):
    print(f'Generating the {args.type} report in the {args.format} format ...\n')
    report=pd.DataFrame()
    output_index=False
    if args.type=='monthly_income':
        assets=pd.read_csv(investment_data['assets'].filename)
        report_series={'name': assets['name']}
        for account in AccountTypes:
            report_series[account]=assets[account].mul(assets['income_per_unit_period']).divide(assets['income_freq_months'])
        report_series['total_rrsp']=report_series['sdrsp'].add(report_series['locked_sdrsp'])
        report_series['total_nonrrsp']=report_series['margin'].add(report_series['tfsa'])
        report=pd.DataFrame(report_series)
        monthly_by_account=pd.DataFrame([['TOTAL MONTHLY']+[series.sum() for label,series in report.items() if label!='name']],
                                         columns=investment_data[args.type].columns[:-2])
        report=pd.concat([report,monthly_by_account],ignore_index=True)
        report['monthly_total']=report['resp'].add(report['total_rrsp']).add(report['total_nonrrsp'])
        monthly_totals=report[report['name']=='TOTAL MONTHLY']
        report['yearly_total']=report['monthly_total'].mul(12)
        monthly_totals=pd.DataFrame([['TOTAL YEARLY']+[series.sum()*12 for label,series in monthly_totals.items() if label!='name' and label!='yearly_total']],
                                       columns=investment_data[args.type].columns[:-1])
        report=pd.concat([report,monthly_totals],ignore_index=True)
        report.at[report.shape[0]-1,'yearly_total']=0
    elif args.type=='tfsa_summary':
        trans=pd.read_csv(investment_data['transactions'].filename)
        tfsa_trans=trans[((trans['type'].isin(['cont','cont_limit'])) & (trans['account']=='tfsa')) | (trans['xfer_account']=='tfsa')]
        pd.set_option('mode.chained_assignment',None)
        tfsa_xfer_trans=tfsa_trans['type']=='xfer'
        tfsa_trans.loc[tfsa_xfer_trans,['type']]='xfer_in'
        pd.set_option('mode.chained_assignment','warn')
        report=tfsa_trans.groupby(['type']).sum()
        report['num_transactions']=tfsa_trans.groupby(['type']).size()
        report=report[['num_transactions','total']]
        print(f"\nTotal Contribution Room = ${report['total']['cont_limit']-report['total']['cont']-report['total']['xfer_in']:,.2f}\n")
        output_index=True
    print(report.to_string(index=output_index, show_dimensions=True,float_format=lambda x: '$%.2f'%x))
    if args.format=='csv':
        fname=investment_data[args.type].filename
        fname_ts=fname.with_stem(fname.stem+'_'+strftime("%Y-%m-%d-%H_%M_%S",localtime()))
        report.to_csv(fname_ts, index=output_index)
        report.to_csv(fname, index=output_index)
        print(f'Report written to "{fname_ts}", and "{fname}" updated accordingly')
    return settings

def list_data(args, settings):
    df=pd.read_csv(investment_data[args.list].filename)
    if args.filter:
        filter=eval(args.filter)
        df=df[filter]
    print(df.to_string(index=False, na_rep='', show_dimensions=True,float_format=lambda x: '$%.2f'%x))
    return settings

def append_csv(data_type, df_to_append):
    print(f'\n{data_type} data to append:\n')
    print(df_to_append.to_string(index=False, show_dimensions=True))
    csv_file_df=pd.read_csv(investment_data[data_type].filename)
    combined_df=pd.concat([csv_file_df, df_to_append])
    print(f'\n{data_type} data appended and written to file:\n')
    print(combined_df.to_string(index=False, na_rep='', show_dimensions=True,float_format=lambda x: '$%.2f'%x),'\n')
    combined_df.to_csv(investment_data[data_type].filename, index=False)

def buy_sell_transaction(args):
    assets=pd.read_csv(investment_data['assets'].filename, index_col=0)
    try:
        current_acct_units=assets.loc[args.name,args.account]
    except KeyError:
        print(f'ERROR: "{args.name}" does not exist. Create asset before executing transaction.')
        return False

    if args.type=='buy':
        updated_acct_units=current_acct_units+args.units
    elif args.type=='sell':
        updated_acct_units=current_acct_units-args.units
        if updated_acct_units<0:
            print(f'ERROR: Trying to sell more units ("{args.units}") than exist ("{current_acct_units}") in account "{args.account}"')
            return False
    print(f'\n{args.type} {args.units} units of {args.name} for {args.account} yields {updated_acct_units} units from {current_acct_units} units')

    assets.loc[args.name,args.account]=updated_acct_units
    print('\n',assets.to_string(show_dimensions=True),'\n')
    assets.to_csv(investment_data['assets'].filename)
    total_cost=round((args.units*args.amount)+args.fees,2)
    df=pd.DataFrame([[args.date.strftime("%Y-%m-%d"),args.type,args.name,args.account,'',args.units,round(args.amount,2),round(args.fees,2),total_cost]],
                    columns=investment_data['transactions'].columns)
    append_csv('transactions', df)
    return True

def xfer_transaction(args):
    if not args.xfer_account:
        print(f'ERROR: A xfer transaction requires a target account to receive the transfer ("--xfer_account").')
        return False
    assets=pd.read_csv(investment_data['assets'].filename, index_col=0)
    try:
        current_acct_units=assets.loc[args.name,args.account]
        current_xfer_acct_units=assets.loc[args.name,args.xfer_account]
    except KeyError:
        print(f'ERROR: "{args.name}" does not exist. Create asset before executing transaction.')
        return False

    updated_acct_units=current_acct_units-args.units
    if updated_acct_units<0:
        print(f'ERROR: Trying to transfer more units ("{args.units}") than exist ("{current_acct_units}") in account "{args.account}"')
        return False

    updated_xfer_acct_units=current_xfer_acct_units+args.units
    print(f'Transferring {args.units} units of {args.name} from {args.account} to {args.xfer_account} accounts yields:')
    print(f'  {args.account:12}: {current_acct_units:8} ▶︎ {updated_acct_units:8} units')
    print(f'  {args.xfer_account:12}: {current_xfer_acct_units:8} ▶︎ {updated_xfer_acct_units:8} units')
    assets.loc[args.name,args.account]=updated_acct_units
    assets.loc[args.name,args.xfer_account]=updated_xfer_acct_units
    print('\n',assets.to_string(show_dimensions=True),'\n')
    assets.to_csv(investment_data['assets'].filename)
    total_cost=round((args.units*args.amount)+args.fees,2)
    df=pd.DataFrame([[args.date.strftime("%Y-%m-%d"),args.type,args.name,args.account,args.xfer_account,args.units,round(args.amount,2),round(args.fees,2),total_cost]],
                    columns=investment_data['transactions'].columns)
    append_csv('transactions', df)
    return True

def contribute_transaction(args):
    if args.amount<0:
        print(f'ERROR: Must contribute more than $0 "--amount=={args.amount} <= 0"')
        return False
    if args.type=='cont' and args.name!='cash':
        print(f'ERROR: Cash contribution only (i.e. "--name==cash")')
        return False
    if args.type=='cont_limit' and args.name!='any':
        print(f'ERROR: Contribution limit can be for anything (i.e. "--name==any")')
        return False
    df=pd.DataFrame([[args.date.strftime("%Y-%m-%d"),args.type,args.name,args.account,'',args.units,round(args.amount,2),round(args.fees,2),round((args.units*args.amount)+args.fees,2)]],
                    columns=investment_data['transactions'].columns)
    append_csv('transactions', df)
    return True

process_transaction={'buy': buy_sell_transaction,
                     'sell': buy_sell_transaction,
                     'xfer': xfer_transaction,
                     'cont': contribute_transaction,
                     'cont_limit': contribute_transaction,
                    }

def asset_transactions(args, settings):
    if not process_transaction[args.type](args):
        print(f'ERROR: {args.type} transaction was not successful.')
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

dispatch={'transact': asset_transactions,
          'datapath': datapath,
          'verbosity': verbosity,
          'list': list_data,
          'income': income_received,
          'report': generate_report,
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