#!/usr/bin/env python3

import argparse
import math
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
ReportTypes=['monthly_income','monthly_income_actual','monthly_income_schedule','tfsa_summary']
ReportFormats=['csv']
TransactionTypes=['buy','sell','xfer','cont','cont_limit','div','withdraw']

investment_data={'assets': InvestmentDataDetails(filename=Path('assets.csv'),
                                                 columns=['name','market','type','subtype','income_per_unit_period','sdrsp','locked_sdrsp','margin','tfsa','resp','income_freq_months','income_first_month','income_day_of_month'],
                                                 description='ledger of owned financial instruments'),
                 'monthly_income': InvestmentDataDetails(filename=Path('income_monthly.csv'),
                                                         columns=['name','sdrsp','locked_sdrsp','margin','tfsa','resp','total_rrsp','total_nonrrsp','monthly_total','yearly_total'],
                                                         description='projected monthly income by account, including overall & RRSP and non-registered totals'),
                 'monthly_income_schedule': InvestmentDataDetails(filename=Path('income_monthly_sched.csv'),
                                                                  columns=['name','jan_rrsp','jan_nonrrsp','feb_rrsp','feb_nonrrsp','mar_rrsp','mar_nonrrsp','apr_rrsp','apr_nonrrsp','may_rrsp','may_nonrrsp','jun_rrsp','jun_nonrrsp','jul_rrsp','jul_nonrrsp','aug_rrsp','aug_nonrrsp','sep_rrsp','sep_nonrrsp','oct_rrsp','oct_nonrrsp','nov_rrsp','nov_nonrrsp','dec_rrsp','dec_nonrrsp'],
                                                                  description='projected monthly income schedule'),
                 'monthly_income_actual': InvestmentDataDetails(filename=Path('income_monthly_actual.csv'),
                                                                columns=['name','sdrsp','locked_sdrsp','margin','tfsa','resp','total_rrsp','total_nonrrsp','monthly_total','yearly_total'],
                                                                description='actual monthly income by account, including overall & RRSP and non-registered totals'),
                 'tfsa_summary': InvestmentDataDetails(filename=Path('tfsa_summary.csv'),
                                                       columns=['num','total'],
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
                                      help='price of a stock unit, dividend per unit, or contribution amount per unit')
    clp_command_transact.add_argument('--date',
                                      type=date.fromisoformat,
                                      default=date.today(),
                                      help='transaction date (e.g. "2021-03-31")')
    clp_command_transact.add_argument('--fees',
                                      type=float,
                                      default=0.00,
                                      help='total transaction fees (default: "0.00")')

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

def write_data_file(file_type, df, data_type, output_index):
    if file_type=='csv':
        fname=investment_data[data_type].filename
        fname_ts=fname.with_stem(fname.stem+'_'+strftime("%Y-%m-%d-%H_%M_%S",localtime()))
        df.to_csv(fname_ts, index=output_index)
        df.to_csv(fname, index=output_index)
        print(f'Data written to "{fname_ts}", and "{fname}" updated accordingly')

def gen_report_monthly_income():
    report=pd.DataFrame()
    output_index=False
    assets=pd.read_csv(investment_data['assets'].filename)
    report_series={'name': assets['name']}
    for account in AccountTypes:
        report_series[account]=assets[account].mul(assets['income_per_unit_period']).divide(assets['income_freq_months'])
    report_series['total_rrsp']=report_series['sdrsp'].add(report_series['locked_sdrsp'])
    report_series['total_nonrrsp']=report_series['margin'].add(report_series['tfsa'])
    report=pd.DataFrame(report_series)
    monthly_by_account=pd.DataFrame([['TOTAL MONTHLY']+[series.sum() for label,series in report.items() if label!='name']],
                                     columns=investment_data['monthly_income'].columns[:-2])
    report=pd.concat([report,monthly_by_account],ignore_index=True)
    report['monthly_total']=report['resp'].add(report['total_rrsp']).add(report['total_nonrrsp'])
    monthly_totals=report[report['name']=='TOTAL MONTHLY']
    report['yearly_total']=report['monthly_total'].mul(12)
    monthly_totals=pd.DataFrame([['TOTAL YEARLY']+[series.sum()*12 for label,series in monthly_totals.items() if label!='name' and label!='yearly_total']],
                                   columns=investment_data['monthly_income'].columns[:-1])
    report=pd.concat([report,monthly_totals],ignore_index=True)
    report.at[report.shape[0]-1,'yearly_total']=0
    return report, output_index

def gen_report_monthly_income_sched():
    report=pd.DataFrame()
    output_index=True
    assets=pd.read_csv(investment_data['assets'].filename, index_col=0)
    income={}
    for account in AccountTypes:
        income[account]=assets[account].mul(assets['income_per_unit_period'])
    income['rrsp']=income['sdrsp'].add(income['locked_sdrsp'])
    income['nonrrsp']=income['margin'].add(income['tfsa'])
    for account in AccountTypes:
        del income[account] 
    sched={col: [] for col in investment_data['monthly_income_schedule'].columns[1:]}
    for row, (name, details) in enumerate(assets.iterrows()):
        freq=details['income_freq_months']
        starting_month=details['income_first_month']
        for month in range(1,13):
            if month>=starting_month:
                inc_rrsp=income['rrsp'][row] if ((month-starting_month)%freq==0) else 0.0
                inc_nonrrsp=income['nonrrsp'][row] if ((month-starting_month)%freq==0) else 0.0
            else:
                inc_rrsp=inc_nonrrsp=0.0
            sched[investment_data['monthly_income_schedule'].columns[month*2-1]].append(inc_rrsp)
            sched[investment_data['monthly_income_schedule'].columns[month*2]].append(inc_nonrrsp)
    report=pd.DataFrame(data=sched,index=assets.index)
    monthly_totals=pd.DataFrame([[series.sum() for label,series in report.items()]],
                                columns=investment_data['monthly_income_schedule'].columns[1:],
                                index=pd.Series(data={name:'TOTAL'},name='name'))
    report=pd.concat([report,monthly_totals])
    return report, output_index

def gen_report_monthly_income_actual():
    report=pd.DataFrame()
    output_index=True
    assets=pd.read_csv(investment_data['assets'].filename, index_col=0)
    trans=pd.read_csv(investment_data['transactions'].filename, index_col=0)
    div_trans=trans[trans['type']=='div']
    asset_index=[]
    income={col: [] for col in investment_data['monthly_income_actual'].columns[1:]}
    for i, (n,a) in enumerate(assets.iterrows()):
        asset_index.append(n)
        income_freq=a['income_freq_months']
        for acct in AccountTypes:
            if a[acct]>0:
                acct_divs=div_trans[(div_trans['name']==n)&(div_trans['account']==acct)].sort_values('date')
                try:
                    div_income=acct_divs['total'][acct_divs.last_valid_index()]
                except KeyError:
                    div_income=0.0
            else:
                div_income=0.0
            income[acct].append(div_income/income_freq)
        income['total_rrsp'].append(income['sdrsp'][i]+income['locked_sdrsp'][i])
        income['total_nonrrsp'].append(income['margin'][i]+income['tfsa'][i])
        income['monthly_total'].append(income['total_rrsp'][i]+income['total_nonrrsp'][i]+income['resp'][i])
        income['yearly_total'].append(income['monthly_total'][i]*12)

    asset_index.extend(['TOTAL_MONTHLY','TOTAL_YEARLY'])
    for col in income:
        monthly_total=math.fsum(income[col])
        income[col].append(monthly_total)
        income[col].append(monthly_total*12)
    income['yearly_total'][len(asset_index)-1]=0.0
    index_df=pd.Series(data=asset_index,name='name')
    report=pd.DataFrame(data=income,index=index_df)
    return report, output_index

def gen_report_tfsa_summary():
    report=pd.DataFrame()
    output_index=True
    trans=pd.read_csv(investment_data['transactions'].filename)
    tfsa_trans=trans[((trans['type'].isin(['cont','cont_limit','withdraw'])) & (trans['account']=='tfsa')) | (trans['xfer_account']=='tfsa')]
    pd.set_option('mode.chained_assignment',None)
    tfsa_xfer_trans=tfsa_trans['type']=='xfer'
    tfsa_trans.loc[tfsa_xfer_trans,['type']]='xfer_in'
    pd.set_option('mode.chained_assignment','warn')
    report=tfsa_trans.groupby(['type']).sum()
    report['num']=tfsa_trans.groupby(['type']).size()
    report=report[['num','total']]
    try:
        cont_limit_sum=report['total']['cont_limit']
    except KeyError:
        cont_limit_sum=0.0
    try:
        withdraw_sum=report['total']['withdraw']
    except KeyError:
        withdraw_sum=0.0
    try:
        cont_sum=report['total']['cont']
    except KeyError:
        cont_sum=0.0
    try:
        xfer_in_sum=report['total']['xfer_in']
    except KeyError:
        xfer_in_sum=0.0
    cont_room=cont_limit_sum+withdraw_sum-cont_sum-xfer_in_sum
    print(f"\nTotal Contribution Room = ${cont_room:,.2f} (cont_limit + withdraw - cont - xfer_in\n")
    contrib_room=pd.DataFrame({'num':1, 'total':cont_room}, index=pd.Series(data={'type':'cont_room'},index=['type'],name='type'))
    report=pd.concat([report,contrib_room])
    return report, output_index

gen_report={'monthly_income': gen_report_monthly_income,
            'monthly_income_actual': gen_report_monthly_income_actual,
            'monthly_income_schedule': gen_report_monthly_income_sched,
            'tfsa_summary': gen_report_tfsa_summary,
           }

def generate_report(args, settings):
    print(f'Generating the {args.type} report in the {args.format} format ...\n')
    report, output_index=gen_report[args.type]()
    print(report.to_string(index=output_index, show_dimensions=True,float_format=lambda x: '$%.2f'%x))
    write_data_file(args.format, report, args.type, output_index)
    return settings

def list_data(args, settings):
    df=pd.read_csv(investment_data[args.list].filename)
    if args.filter:
        filter=eval(args.filter)
        df=df[filter]
    if args.list=='assets':
        float_format=lambda x: '$%.5f'%x
    else:
        float_format=lambda x: '$%.2f'%x
    print(df.to_string(index=False, na_rep='', show_dimensions=True,float_format=float_format))
    return settings

def append_csv(data_type, df_to_append):
    print(f'\n{data_type} data to append:\n')
    print(df_to_append.to_string(index=False, show_dimensions=True))
    csv_file_df=pd.read_csv(investment_data[data_type].filename)
    combined_df=pd.concat([csv_file_df, df_to_append])
    print(f'\n{data_type} data appended and written to file:\n')
    print(combined_df.to_string(index=False, na_rep='', show_dimensions=True,float_format=lambda x: '$%.2f'%x),'\n')
    write_data_file('csv', combined_df, data_type, False)

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
    write_data_file('csv', assets, 'assets', True)
    total_cost=round((args.units*args.amount)+args.fees,2)
    df=pd.DataFrame([[args.date.strftime("%Y-%m-%d"),args.type,args.name,args.account,'',args.units,round(args.amount,2),round(args.fees,2),total_cost]],
                    columns=investment_data['transactions'].columns)
    append_csv('transactions', df)
    return True

def dividend_transaction(args):
    assets=pd.read_csv(investment_data['assets'].filename, index_col=0)
    try:
        dividend=assets.loc[args.name,'income_per_unit_period']
    except KeyError:
        print(f'ERROR: "{args.name}" does not exist. Create asset before executing transaction.')
        return False

    if dividend!=args.amount:
        assets.loc[args.name,'income_per_unit_period']=args.amount
        print(f'\nDividend has changed from {dividend} to {args.amount}\n')
        write_data_file('csv', assets, 'assets', True)

    total_dividend=round((args.units*args.amount)-args.fees,2)
    df=pd.DataFrame([[args.date.strftime("%Y-%m-%d"),args.type,args.name,args.account,'',args.units,args.amount,round(args.fees,2),total_dividend]],
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
    write_data_file('csv', assets, 'assets', True)
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

def withdrawal_transaction(args):
    if args.amount<=0.0:
        print(f'ERROR: Must withdraw more than $0 "--amount=={args.amount} > 0.00"')
        return False
    if args.type=='withdraw' and args.name!='cash':
        print(f'ERROR: Cash withdrawal only (i.e. "--name==cash")')
        return False
    df=pd.DataFrame([[args.date.strftime("%Y-%m-%d"),args.type,args.name,args.account,'',args.units,round(args.amount,2),round(args.fees,2),round(args.units*args.amount,2)]],
                    columns=investment_data['transactions'].columns)
    append_csv('transactions', df)
    return True

process_transaction={'buy': buy_sell_transaction,
                     'sell': buy_sell_transaction,
                     'xfer': xfer_transaction,
                     'cont': contribute_transaction,
                     'cont_limit': contribute_transaction,
                     'div': dividend_transaction,
                     'withdraw': withdrawal_transaction,
                    }

def asset_transactions(args, settings):
    if not process_transaction[args.type](args):
        print(f'ERROR: {args.type} transaction was not successful.')
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