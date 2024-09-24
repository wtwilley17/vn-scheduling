import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import pandas as pd
import io
import csv
from datetime import datetime, date, timedelta
from pulp import *
import numpy as np
from itertools import product
from calendar import monthrange
import random
import warnings
from dateutil.relativedelta import relativedelta, MO
from pandas.tseries.offsets import MonthEnd
warnings.filterwarnings("ignore")

# This is a server module. It runs on the Anvil server,
# rather than in the user's browser.
#
# To allow anvil.server.call() to call functions here, we mark
# them with @anvil.server.callable.
# Here is an example - you can replace it with your own:
#
# @anvil.server.callable
# def say_hello(name):
#   print("Hello, " + name + "!")
#   return 42
#

@anvil.server.callable
def store_agent_data(file):
  # Reset Table
  app_tables.agent_data.delete_all_rows()
  file = file.get_bytes()
  # Decode bytes to string
  data_str = file.decode('utf-8')
  # Use io.StringIO to convert the string to a file-like object
  data_io = io.StringIO(data_str)
  # Read and process CSV
  csv_reader = csv.reader(data_io)
  # Skip Header
  headers = next(csv_reader)
  # Insert to table
  for row in csv_reader:
    app_tables.agent_data.add_row(agent_id=row[0],role=row[1],stat=row[2])

@anvil.server.callable
def store_leave_data(file):
  # Reset Table
  app_tables.agent_leave.delete_all_rows()
  file = file.get_bytes()
  # Decode bytes to string
  data_str = file.decode('utf-8')
  # Use io.StringIO to convert the string to a file-like object
  data_io = io.StringIO(data_str)
  # Read and process CSV
  csv_reader = csv.reader(data_io)
  # Skip Header
  headers = next(csv_reader)
  # Insert to table
  for row in csv_reader:
    app_tables.agent_leave.add_row(date_leave=pd.to_datetime(row[0]).date(),name=row[1],reason=row[2])

@anvil.server.callable
def store_df1bas():
  # Reset Table
  app_tables.df1_bas.delete_all_rows()
  df = create_df1_bas()
  for index, row in df.iterrows():
    app_tables.df1_bas.add_row(name=row['name'], reason=row['reason'],daynum=row['daynum'])



### Scheduling ####
def dummy_df(start, end, x):
  date_range = pd.date_range(start, end)
  repeated_dates = date_range.repeat(x)
  df = pd.DataFrame(repeated_dates, columns=['date1'])
  df['date1']=pd.to_datetime(df['date1']).dt.date
  return df
  
def create_date():
  # Get the first date for next month
  today = datetime.today()
  date1_next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
  
  # Get the last 2 monday from this month
  last2_monday = date1_next_month + relativedelta(weekday=MO(-2))
  
  # End of this month date
  end_mo = today + MonthEnd(0)
  end_mo2 = date1_next_month + MonthEnd(0)
  
  print(date1_next_month.strftime("%Y-%m-%d"))
  print(last2_monday.strftime("%Y-%m-%d"))
  print(end_mo.strftime("%Y-%m-%d"))
  print(end_mo2.strftime("%Y-%m-%d"))
  
  delta = end_mo2.date() - last2_monday.date()
  num_days1 =delta.days+1
  num_days2 =delta.days+2
  delta_days = num_days1*14
  return date1_next_month,last2_monday,end_mo,end_mo2,num_days1,num_days2,delta_days

def create_df1_bas():
  df1_bas_records = app_tables.agent_leave.search()
  dicts = [{'date_leave': r['date_leave'], 'name': r['name'], 'reaseon': r['reason']} for r in df1_bas_records]
  df1_bas = pandas.DataFrame.from_dict(dicts)
  df1_bas.date_leave = pd.to_datetime(df1_bas.date_leave)
  date1_next_month,last2_monday,end_mo,end_mo2,num_days1,num_days2,delta_days = create_date()
  date_range = pd.date_range(last2_monday,end_mo2).tolist()
  dfdm = pd.DataFrame(date_range, columns=['date'])
  dfdm['daynum'] = [i for i in range(1,num_days2)]
  dfdm['date'] = pd.to_datetime(dfdm['date']).dt.normalize()
  df1_bas = df1_bas.merge(dfdm,right_on='date',left_on='date_leave')
  df1_bas = df1_bas[['name','reason','daynum']]
  return df1_bas

def create_dh1():
  dh1 = dummy_df(date1_next_month,end_mo2,14)
  dh1.date1 = pd.to_datetime(dh1.date1)
  dh1['name day'] = dh1.date1.dt.day_name()
  dh1['hr1'] =dh1.date1.dt.hour
  dh1['day'] = dh1.date1.dt.day
  dh1['check_holiday'] = 0

def create_df():
  df =dummy_df(last2_monday,end_mo2,14)
  df.date1 = pd.to_datetime(df.date1)
  df = df.merge(dfdm, left_on='date1',right_on='date')
  df['hr1'] = df.date1.dt.hour
  df['day'] = df.date1.dt.day