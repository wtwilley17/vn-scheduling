import anvil.secrets
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import anvil.media
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
import xlrd
from dateutil.relativedelta import relativedelta, MO
from pandas.tseries.offsets import MonthEnd
import psycopg2
import psycopg2.extras
from .query import *

@anvil.server.callable
def store_agent_data(file):
  # Reset Table
  app_tables.agent_list.delete_all_rows()
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
    app_tables.agent_list.add_row(agent_id=row[0],role=row[1],stat=row[2])
  

  
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
  date_io2 = io.StringIO(data_str)
  df = pd.read_csv(date_io2)
  msg = leave_check(df)
  return msg
  
@anvil.server.callable
def store_df1bas():
  # Reset Table
  app_tables.df1_bas.delete_all_rows()
  dfdm = create_dfdm()
  df = create_df1_bas(dfdm)
  for index, row in df.iterrows():
    app_tables.df1_bas.add_row(name=row['name'], reason=row['reason'],daynum=row['daynum'])

@anvil.server.callable
def scheduling(holiday_dates,a1,a2,a5):
  global df1_bas,df2_bas,dh1
  dh1 = create_dh1(holiday_dates)
  df1_bas = create_df1_bas(dfdm)
  df2_bas = create_df2_bas()
  app_tables.final.delete_all_rows()
  Dt_bas, Dt__bas, status, supply, demand = capacity_vn_ca(a1,a2,a5)
  if status == 'Optimal':
    final = str_func(Dt_bas=Dt_bas, Dt__bas=Dt__bas)
    for d in final.to_dict(orient="records"):
        # d is now a dict of {columnname -> value} for this row
        # We use Python's **kwargs syntax to pass the whole dict as
        # keyword arguments
        app_tables.final.add_row(**d)
    final.to_csv('/tmp/final.csv',index=False)
    return final.to_markdown() ,supply, demand
  elif status == 'Infeasible':
    return status, supply, demand
    
  
@anvil.server.callable
def get_csv():
  media = anvil.media.from_file('/tmp/final.csv', 'csv', 'final.csv')
  return media


@anvil.server.callable
def get_agent_leave_pg():
  print('connecting')
  conn = connect()
  print('connected',conn)
  with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
    cur.execute(query_leave)
    return cur.fetchall()
  

### Function ####

def connect():
  connection = psycopg2.connect(dbname='appsheet_ops',
                                host='pgm-d9jxszcmh2pvzi140o.pgsql.ap-southeast-5.rds.aliyuncs.com',
                                user='ops_appsheet_prod',
                                password=anvil.secrets.get_secret('db_password'))
                                #password='WTzQLgYh7EwwZVx6i7ayp5jei3dryk3w')
  return connection
  
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
  
  delta = end_mo2.date() - last2_monday.date()
  num_days1 =delta.days+1
  num_days2 =delta.days+2
  delta_days = num_days1*14
  return date1_next_month,last2_monday,end_mo,end_mo2,num_days1,num_days2,delta_days

def create_df1_bas(dfdm):
  df1_bas_records = app_tables.agent_leave.search()
  dicts = [{'date_leave': r['date_leave'], 'name': r['name'], 'reason': r['reason']} for r in df1_bas_records]
  df1_bas = pd.DataFrame.from_dict(dicts)
  df1_bas.date_leave = pd.to_datetime(df1_bas.date_leave)
  date1_next_month,last2_monday,end_mo,end_mo2,num_days1,num_days2,delta_days = create_date()
  date_range = pd.date_range(last2_monday,end_mo2).tolist()
  df1_bas = df1_bas.merge(dfdm,right_on='date',left_on='date_leave')
  df1_bas = df1_bas[['name','reason','daynum']]
  return df1_bas

def create_df2_bas():
  df2_bas_records = app_tables.agent_list.search()
  dicts = [{'agent_id': r['agent_id'], 'role': r['role'], 'stat': r['stat']} for r in df2_bas_records]
  df2_bas = pd.DataFrame.from_dict(dicts)
  return df2_bas

def create_dfdm():
  date_range = pd.date_range(last2_monday,end_mo2).tolist()
  dfdm = pd.DataFrame(date_range, columns=['date'])
  dfdm['daynum'] = [i for i in range(1,num_days2)]
  dfdm['date'] = pd.to_datetime(dfdm['date']).dt.normalize()
  return dfdm

def create_dh1(holiday_dates):
  holiday_dates = [pd.to_datetime(i) for i in holiday_dates]
  dh1 = dummy_df(date1_next_month,end_mo2,14)
  dh1.date1 = pd.to_datetime(dh1.date1)
  dh1['name day'] = dh1.date1.dt.day_name()
  dh1['hr1'] =dh1.date1.dt.hour
  dh1['day'] = dh1.date1.dt.day
  dh1['check_holiday'] = 0
  for index, row in dh1.iterrows():
    if row['date1'] in holiday_dates:
      dh1.at[index, 'check_holiday'] = 1
  return dh1

def leave_check(df):
  message = ''
  request_date = []
  agent_list = list(df.name.unique())
  # loop for every agent
  for i in agent_list:
    df_temp = df[df.name == i].reset_index(drop=True)
    # create a temporary df for each agent
    for index, row in df_temp.iterrows():
    # loop each agent leave request
      if index < len(df_temp)-1: 
        list_temp = list(df_temp.loc[[index, index+1], 'date_leave'])
        req_delta = pd.to_datetime(list_temp[1]) - pd.to_datetime(list_temp[0])
        #print(list_temp,req_delta)
        #work - holiday - work
        if req_delta.days == 2:
          # check the request type
          leave_type = list(df_temp.loc[[index, index+1], 'reason'])
          print(leave_type[0],leave_type[1])
          if leave_type[0] == leave_type[1] == 'DO':
            message += f'{i} Work - Off - Work on {list_temp[0]} and {list_temp[1]}\n'
          #elif req_delta > 5:
          # check if its within the same week
  #print(message)
  return message
        
          
          
        

def create_df(dfdm):
  df =dummy_df(last2_monday,end_mo2,14)
  df.date1 = pd.to_datetime(df.date1)
  df = df.merge(dfdm, left_on='date1',right_on='date')
  df['hr1'] = df.date1.dt.hour
  df['day'] = df.date1.dt.day
  return df

def capacity_vn_ca(a1_agent=1,a2_agent=1,a5_agent=2):
    now = datetime.now()
    next_month = now + relativedelta(months=+1)
    year = next_month.year
    month = next_month.month
    tot_days = monthrange(year, month)[1]
    num_days= (delta_days//14) 
    hours = num_days*14-13 
    i_s = df2_bas['agent_id'].unique().tolist()
    i_s = random.sample(i_s, len(i_s))
    j_s =list(range(1,hours+14))
    w_s = list(range(0,hours,14))
    shift_supply = []
    model = LpProblem("Capacity", LpMinimize)
    
    y = LpVariable.dicts("y", (i_s,j_s), 0, 1, cat='Binary') #shift 1:8-17  ->Shift A2
    x = LpVariable.dicts("x", (i_s,j_s), 0, 1, cat='Binary') #shift 2:8-17 -> Shift A1
    b = LpVariable.dicts("b", (i_s,j_s), 0, 1, cat='Binary') #shift 3:11-20
    c = LpVariable.dicts("c", (i_s,j_s), 0, 1, cat='Binary') #shift 4:13-21 -> Shift D
    
    a2 = LpVariable.dicts("a2", (i_s,w_s), 0, 1, cat='Binary') #shift 1:8-17 -> Shift A2
    a1 = LpVariable.dicts("a1", (i_s,w_s), 0, 1, cat='Binary') #shift 2:8-17 -> Shift A1
    a4 = LpVariable.dicts("a4", (i_s,w_s), 0, 1, cat='Binary') #shift 3:11-20
    a5 = LpVariable.dicts("a5", (i_s,w_s), 0, 1, cat='Binary') #shift 4:13-21 -> Shift D
    
    ab=[]
    for d in range(1,num_days+1):
            ab.append(LpVariable.dicts("ab%s" %d, (i_s), 0, 1, cat='Binary'))
  
    model += lpSum([x[i][j] + y[i][j] + b[i][j] + c[i][j] for i,j in product(i_s,j_s)])

    #Break Time
    for i in i_s:
        for w in w_s:
            model += x[i][4+w] + x[i][5+w] + x[i][6+w]== 2*a1[i][w]              
            model += y[i][4+w] + y[i][5+w] + y[i][6+w] == 2*a2[i][w]
            model += b[i][7+w] + b[i][8+w] + b[i][9+w] == 2*a4[i][w]
            model += c[i][9+w] + c[i][10+w] + c[i][11+w] == 2*a5[i][w]

    #Stop Time
    for i in i_s:
        for w in w_s:
            model += x[i][10+w] + x[i][11+w] + x[i][12+w] + x[i][13+w] + x[i][14+w]  == 0 
            model += y[i][10+w] + y[i][11+w] + y[i][12+w] + y[i][13+w] + y[i][14+w] == 0 
            model += b[i][1+w] + b[i][2+w] + b[i][3+w] + b[i][13+w] + b[i][14+w] == 0
            model += c[i][1+w] + c[i][2+w] + c[i][3+w] + c[i][4+w] + c[i][5+w] == 0
                
    #Working Hours
    for i in i_s:
        for w in w_s:
            model += x[i][1+w] + x[i][2+w] + x[i][3+w] + x[i][5+w] + x[i][7+w] + x[i][8+w] + x[i][9+w]  == 7*a1[i][w]              
            model += y[i][1+w] + y[i][2+w] + y[i][3+w] + y[i][5+w] + y[i][7+w] + y[i][8+w] + y[i][9+w]  == 7*a2[i][w]
            model += b[i][4+w] + b[i][5+w] + b[i][6+w]  + b[i][10+w] + b[i][11+w] + b[i][12+w] == 6*a4[i][w]
            model += c[i][6+w] + c[i][7+w] + c[i][8+w] + c[i][12+w] + c[i][13+w] + c[i][14+w] == 6*a5[i][w]

#     real = df['agent_realtime'].to_list()
#     backlog = df['agent_backlog'].to_list()
    
    #1 Agent 1 Shift / Day
    for i in i_s:
        for w in w_s:
            model += a1[i][w] + a2[i][w] + a4[i][w] + a5[i][w] == 1*ab[w//14][i]
    
    #jika ada yg masuk shift 3, esok harinya tidak masuk shift1 ataupun BK
    for i in i_s:
        for w in w_s[:-1]:
            model += a5[i][w] + a1[i][w+14] <= 1
                    
    for i in i_s:
        for w in w_s[:-1]:
            model += a5[i][w] + a2[i][w+14] <= 1

   
    # minggu 0 (last bulan sebelumnya)
    for i in i_s:
        if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=1) & (df1_bas['daynum']<=7)) & (df1_bas['reason'] != 'DO')]) > 4:
            model += ab[0][i]+ab[1][i]+ab[2][i]+ab[3][i]+ab[4][i]+ab[5][i]+ab[6][i]>= 0
        else:
            model += ab[0][i]+ab[1][i]+ab[2][i]+ab[3][i]+ab[4][i]+ab[5][i]+ab[6][i]>= 4 - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=1) & (df1_bas['daynum']<=7)) & (df1_bas['reason'] != 'DO')])

    for i in i_s:
        if dh1['date1'][0].strftime("%A") == 'Monday':
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=8) & (df1_bas['daynum']<=14)) & (df1_bas['reason'] != 'DO')]) > 4:
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]+ab[13][i]>= 0
            else:
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]+ab[13][i]>= 4 - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=8) & (df1_bas['daynum']<=14)) & (df1_bas['reason'] != 'DO')])
        
        elif dh1['date1'][0].strftime("%A") == 'Tuesday':
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=8) & (df1_bas['daynum']<=14)) & (df1_bas['reason'] != 'DO')]) > 4:
                model += ab[7][i]>=0
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]+ab[13][i]>= 0
            else:
                model += ab[7][i]>=0
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]+ab[13][i]>= 4 - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=8) & (df1_bas['daynum']<=14)) & (df1_bas['reason'] != 'DO')])
        
        elif dh1['date1'][0].strftime("%A") == 'Wednesday':
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=8) & (df1_bas['daynum']<=14)) & (df1_bas['reason'] != 'DO')]) > 4:
                model += ab[7][i]+ab[8][i]>=0
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]+ab[13][i]>= 0
            else:
                model += ab[7][i]+ab[8][i]>=0
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]+ab[13][i]>= 4 - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=8) & (df1_bas['daynum']<=14)) & (df1_bas['reason'] != 'DO')])
        
        elif dh1['date1'][0].strftime("%A") == 'Thursday':
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=8) & (df1_bas['daynum']<=14)) & (df1_bas['reason'] != 'DO')]) > 4:
                model += ab[7][i]+ab[8][i]+ab[9][i]>=0
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]+ab[13][i]>= 0
            else:
                model += ab[7][i]+ab[8][i]+ab[9][i]>=0
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]+ab[13][i]>= 4 - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=8) & (df1_bas['daynum']<=14)) & (df1_bas['reason'] != 'DO')])
        
        elif dh1['date1'][0].strftime("%A") == 'Friday':
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=8) & (df1_bas['daynum']<=14)) & (df1_bas['reason'] != 'DO')]) > 4:
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]>=0
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]+ab[13][i]>= 0
            else:
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]>=0
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]+ab[13][i]>= 4 - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=8) & (df1_bas['daynum']<=14)) & (df1_bas['reason'] != 'DO')])

        elif dh1['date1'][0].strftime("%A") == 'Saturday':
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=8) & (df1_bas['daynum']<=14)) & (df1_bas['reason'] != 'DO')]) > 4:
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]>=0
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]+ab[13][i]>= 0
            else:
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]>=0
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]+ab[13][i]>= 4 - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=8) & (df1_bas['daynum']<=14)) & (df1_bas['reason'] != 'DO')])
        
        elif dh1['date1'][0].strftime("%A") == 'Sunday':
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=8) & (df1_bas['daynum']<=14)) & (df1_bas['reason'] != 'DO')]) > 4:
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]>=0
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]+ab[13][i]>= 0
            else:
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]>=0
                model += ab[7][i]+ab[8][i]+ab[9][i]+ab[10][i]+ab[11][i]+ab[12][i]+ab[13][i]>= 4 - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=8) & (df1_bas['daynum']<=14)) & (df1_bas['reason'] != 'DO')])
     
    #aturan minggu 2                      
    for i in i_s:  
        if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=15) & (df1_bas['daynum']<=21)) & (df1_bas['reason'] != 'DO')]) > 4:
            model += ab[14][i]+ab[15][i]+ab[16][i]+ab[17][i]+ab[18][i]+ab[19][i]+ab[20][i] >= 0
        else:
            model += ab[14][i]+ab[15][i]+ab[16][i]+ab[17][i]+ab[18][i]+ab[19][i]+ab[20][i] >= 4 - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=15) & (df1_bas['daynum']<=21)) & (df1_bas['reason'] != 'DO')])        
    
    #aturan minggu 3
    for i in i_s:  
        if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=22) & (df1_bas['daynum']<=28)) & (df1_bas['reason'] != 'DO')]) > 4:
            model += ab[21][i]+ab[22][i]+ab[23][i]+ab[24][i]+ab[25][i]+ab[26][i]+ab[27][i] >= 0
        else:
            model += ab[21][i]+ab[22][i]+ab[23][i]+ab[24][i]+ab[25][i]+ab[26][i]+ab[27][i] >= 4 - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=22) & (df1_bas['daynum']<=28)) & (df1_bas['reason'] != 'DO')])

          
    #aturan minggu 4
    for i in i_s:  
        if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=29) & (df1_bas['daynum']<=35)) & (df1_bas['reason'] != 'DO')]) > 4:
            model += ab[28][i]+ab[29][i]+ab[30][i]+ab[31][i]+ab[32][i]+ab[33][i]+ab[34][i] >= 0
        else:
            model += ab[28][i]+ab[29][i]+ab[30][i]+ab[31][i]+ab[32][i]+ab[33][i]+ab[34][i] >= 4 - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=29) & (df1_bas['daynum']<=35)) & (df1_bas['reason'] != 'DO')])

    
    #DEFINE UNTUK DIHARI 29,30,31 (MINGUU TERAKHIR PADA AKHIR BULAN YAITU MINGGU 4 DAN 5)
    for i in i_s:
        if num_days== 36:
            model += ab[35][i] >= 0
        elif num_days == 37:
            model += ab[35][i]+ ab[36][i] >= 0 
        elif num_days == 38:
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=38))]) == 3:
                model += ab[35][i]+ab[36][i]+ab[37][i] == 0
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=38))]) == 2:
                model += ab[35][i]+ab[36][i]+ab[37][i] >= 0
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=38))]) <= 1:
                model += ab[35][i]+ab[36][i]+ab[37][i] >= 1    
                    
        elif num_days== 39:
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=39))]) == 4:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i] == 0
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=39))]) == 3:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i] == 1 
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=39))]) == 2:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i] >= 1      
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=39))]) <= 1:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i] >= 1  
        
        elif num_days == 40:
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=40))]) == 5:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i] == 0 
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=40))]) == 4:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i] == 1
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=40))]) == 3:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i] == 2
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=40))]) == 2:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i] == 2
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=40))]) <= 1:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i] >= 2
        
        elif num_days == 41:
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=41))]) == 6:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i]+ab[40][i]>= 0 
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=41))]) == 5:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i]+ab[40][i] >= 1 
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=41))]) == 4:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i]+ab[40][i] >= 2
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=41))]) == 3:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i]+ab[40][i] >= 3
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=41))]) == 2:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i]+ab[40][i] >= 3
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=41))]) <= 1:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i]+ab[40][i] >= 3
        
        elif num_days== 42:
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=42)) & (df1_bas['reason'] != 'DO')]) > 3:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i]+ab[40][i]+ab[41][i] >= 0
            else:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i]+ab[40][i]+ab[41][i] >= 3 - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=42)) & (df1_bas['reason'] != 'DO')])

        elif num_days == 43:
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=42)) & (df1_bas['reason'] != 'DO')]) > 3:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i]+ab[40][i]+ab[41][i] >= 0
            else:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i]+ab[40][i]+ab[41][i] >= 3 - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=42)) & (df1_bas['reason'] != 'DO')])
            model += ab[42][i] >= 0
            
        elif num_days == 44:
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=42)) & (df1_bas['reason'] != 'DO')]) > 4:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i]+ab[40][i]+ab[41][i] >= 0
            else:
                model += ab[35][i]+ab[36][i]+ab[37][i]+ab[38][i]+ab[39][i]+ab[40][i]+ab[41][i] >= 4 - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=36) & (df1_bas['daynum']<=42)) & (df1_bas['reason'] != 'DO')])
            model += ab[42][i]+ab[43][i] >= 0    
            
    #untuk define yg terdata di cs_agent_leave value = 0           
    for w in w_s:
        for i in i_s:
            for k in range(len(df1_bas)):
                if w//14 == df1_bas['daynum'][k]-1 and i == df1_bas['name'][k]:
                    model += ab[w//14][i] == 0
    
    #agent gak boleh mendapat schedule seperti (libur,masuk,libur)
    for w in w_s[:-2]:
        for i in i_s:
            if len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=w//14+1) & (df1_bas['daynum']<=w//14+3))]) == 0: #& (df1_bas['reason'] != 'DO')
                model += ab[w//14][i]+ab[w//14+2][i] >= 1
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=w//14+1) & (df1_bas['daynum']<=w//14+3))]) == 1: #& (df1_bas['reason'] != 'DO')
                model += ab[w//14][i]+ab[w//14+2][i] >= 1
            elif len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=w//14+1) & (df1_bas['daynum']<=w//14+3))]) > 1: #& (df1_bas['reason'] != 'DO')
                model += ab[w//14][i]+ab[w//14+2][i] >= 0
                
    #Maximum working days in a work consecutively 
    for w in w_s[1:-5]:
        for i in i_s:
            model += ab[w//14][i]+ab[w//14+1][i]+ab[w//14+2][i]+ab[w//14+3][i]+ab[w//14+4][i] <= 5-len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>= w//14) & (df1_bas['daynum']<=(w//14+5) )) & (df1_bas['reason'] == 'Annual Leave')])      
    
    
    start = df[df['date1'] == dh1['date1'][0]]['daynum'].iloc[0]-1
    finish = df[df['date1'] == dh1['date1'].iloc[-1]]['daynum'].iloc[0]
             
    #fungsi buat bagi rata
    for i in i_s:
        if i not in df2_bas[(df2_bas['stat']=='nw')]['agent_id'].to_list() and i in df2_bas[df2_bas['role']=='Agent']['agent_id'].to_list(): #- (lpSum([a4[i][w] for w in w_s]) - lpSum([a2[i][w] + a1[i][w] for w in w_s]))
            model += lpSum([a1[i][w] for w in range((start*14), (finish*14),14)]) >= 5#nums1-1#((tot_days - tot_off)//2)-3
            model += lpSum([a1[i][w] for w in range((start*14), (finish*14),14)]) <= 6#((tot_days - tot_off)//2)-3
            model += lpSum([a2[i][w] for w in range((start*14), (finish*14),14)]) >= 5#nums2-e2#((tot_days - tot_off)//2)-3
            model += lpSum([a2[i][w] for w in range((start*14), (finish*14),14)]) <= 6#nums2+e2
            model += lpSum([a5[i][w] for w in range((start*14), (finish*14),14)]) >= 10#nums5-e5#((tot_days - tot_off)//2)-3
            model += lpSum([a5[i][w] for w in range((start*14), (finish*14),14)]) <= 11#nums5+e5#((tot_days - tot_off)//2)-3
            
    new_dh1 = dh1.groupby(['date1','name day'])['name day'].unique().reset_index(name='nm')
    tot_off = len(new_dh1[(new_dh1['name day']=='Saturday') | (new_dh1['name day']=='Sunday')])
        
#     #fungsi baru
    bb = pd.merge(dh1,df[['date1','day','hr1','daynum']],how='inner' ,on=['date1','hr1','day'])
    # ooo = Total Working days in a month (Exclude Public Holiday) 
    ooo = list(bb[bb['check_holiday']==0]['daynum'].unique())
    oo1 = list(bb[bb['check_holiday']==1]['daynum'].unique())
    oo2 = list(bb['daynum'].unique())
    print('Total Working days :',len(ooo))
    print('Total Holidays :',len(oo1))
    print('Total Weekend :',tot_off)
#     public_holiday = 1
#     tot_off = tot_off + public_holiday
    for i in i_s: 
        # Total Working days >= Total Working days - Total weekends - Request Leave / Of   | 28 - 8 - 0 =  20 days
        print(i,len(ooo) -(tot_off) - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=start+1) & (df1_bas['daynum']<=finish))&( df1_bas['reason'] == 'Annual Leave')]))
        working_days = len(ooo) -(tot_off) - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=start+1) & (df1_bas['daynum']<=finish))&( df1_bas['reason'] == 'Annual Leave')])
        shift_supply.append(working_days)
        model += lpSum([ab[w-1][i] for w in ooo]) == len(ooo) -(tot_off) - len(df1_bas[(df1_bas['name']==i) & ((df1_bas['daynum']>=start+1) & (df1_bas['daynum']<=finish))&( df1_bas['reason'] == 'Annual Leave')])

        #     for w in w_s:
#         model+= lpSum([a2[i][w] for i in i_s]) >= lpSum([a4[i][w] for i in i_s])
        
    for w in w_s:
        model+= lpSum([a1[i][w] for i in i_s]) >= 1
        model+= lpSum([a2[i][w] for i in i_s]) >= 1
        model+= lpSum([a4[i][w] for i in i_s]) == 0
        model+= lpSum([a5[i][w] for i in i_s]) >= 2
        
  
    solver=PULP_CBC_CMD(gapRel=0.5, msg=False, timeLimit=300)            
    status=model.solve(solver)
    checking=LpStatus[status]
    print(checking)
    shift_demand = len(oo2) * (a1_agent+a2_agent+a5_agent)
  
    l0 = [x[i][j].name for i,j in product(i_s,j_s)]
    ck = [x[i][j].varValue for i,j in product(i_s,j_s)]
    l1 = [y[i][j].name for i,j in product(i_s,j_s)]
    ck1 = [y[i][j].varValue for i,j in product(i_s,j_s)]
    l4 = [b[i][j].name for i,j in product(i_s,j_s)]
    ck4 = [b[i][j].varValue for i,j in product(i_s,j_s)]
    l5 = [c[i][j].name for i,j in product(i_s,j_s)]
    ck5 = [c[i][j].varValue for i,j in product(i_s,j_s)]
    
    Dt= pd.DataFrame({'sh0_bas': l0, 'val0_bas':ck,'sh1_bas': l1, 'val1_bas':ck1, 'sh2_bas': l4, 'val2_bas':ck4, 'sh3_bas': l5, 'val3_bas':ck5 })

    #list optimization per day
    
    v0 = [a1[i][w].name for i,w in product(i_s,w_s)]
    vk0 = [a1[i][w].varValue for i,w in product(i_s,w_s)]
    v1 = [a2[i][w].name for i,w in product(i_s,w_s)]
    vk1 = [a2[i][w].varValue for i,w in product(i_s,w_s)]
    v4 = [a4[i][w].name for i,w in product(i_s,w_s)]
    vk4 = [a4[i][w].varValue for i,w in product(i_s,w_s)]
    v5 = [a5[i][w].name for i,w in product(i_s,w_s)]
    vk5 = [a5[i][w].varValue for i,w in product(i_s,w_s)]

    Dt_ = pd.DataFrame({'sh0_bas': v0, 'val0_bas':vk0, 'sh1_bas': v1, 'val1_bas':vk1, 'sh2_bas': v4, 'val2_bas':vk4, 'sh3_bas': v5, 'val3_bas':vk5 })
    return Dt, Dt_,checking, sum(shift_supply),shift_demand

def result_basic(Dt_bas, Dt__bas):
    pp = []
    for i in Dt_bas['ag']:
        if i in [x for x in range(1,len(df)+1,14)]: #373
            pp.append(8)
        elif i in [x for x in range(2,len(df)+1,14)]: #373
            pp.append(9)
        elif i in [x for x in range(3,len(df)+1,14)]:
            pp.append(10)
        elif i in [x for x in range(4,len(df)+1,14)]:
            pp.append(11)
        elif i in [x for x in range(5,len(df)+1,14)]:
            pp.append(12)
        elif i in [x for x in range(6,len(df)+1,14)]:
            pp.append(13)
        elif i in [x for x in range(7,len(df)+1,14)]:
            pp.append(14)
        elif i in [x for x in range(8,len(df)+1,14)]:
            pp.append(15)
        elif i in [x for x in range(9,len(df)+1,14)]:
            pp.append(16)
        elif i in [x for x in range(10,len(df)+1,14)]:
            pp.append(17)
        elif i in [x for x in range(11,len(df)+1,14)]:
            pp.append(18)
        elif i in [x for x in range(12,len(df)+1,14)]:
            pp.append(19)
        elif i in [x for x in range(13,len(df)+1,14)]:
            pp.append(20)
        elif i in [x for x in range(14,len(df)+1,14)]:
            pp.append(21)
    Dt_bas['hour'] = pp

    #create day field
    Dt_bas['day'] = Dt_bas.groupby('hour')['ag'].rank(method='dense').astype(int)
    Dt__bas['day'] = Dt__bas['ag']//14+1
    
    #Merge Data
    dayta = pd.merge(Dt_bas,Dt__bas, on=['agent','day'], how='left')
    
    bb = []
    for i in range(len(Dt_bas)): 
        #if Dt_soc['agent'][i] == 1:
        if dayta['val0_bas_y'][i] + dayta['val1_bas_y'][i] + dayta['val2_bas_y'][i]+dayta['val3_bas_y'][i] == 1 and dayta['val0_bas_x'][i] + dayta['val1_bas_x'][i] + dayta['val2_bas_x'][i] + dayta['val3_bas_x'][i] == 0:
            if dayta['val0_bas_x'][i] ==0 and dayta['hour'][i] == 11 and dayta['val0_bas_y'][i]==1 :
                bb.append('A1')
            elif dayta['val0_bas_x'][i] ==0 and dayta['hour'][i] == 12 and dayta['val0_bas_y'][i]==1 :
                bb.append('A1')
            elif dayta['val0_bas_x'][i] ==0 and dayta['hour'][i] == 13 and dayta['val0_bas_y'][i]==1 :
                bb.append('A1')
            elif dayta['val1_bas_x'][i] ==0 and dayta['hour'][i] == 11 and dayta['val1_bas_y'][i]==1 :
                bb.append('A211')    
            elif dayta['val1_bas_x'][i] ==0 and dayta['hour'][i] == 12 and dayta['val1_bas_y'][i]==1 :
                bb.append('A212')  
            elif dayta['val1_bas_x'][i] ==0 and dayta['hour'][i] == 13 and dayta['val1_bas_y'][i]==1 :
                bb.append('A213')    
            elif dayta['val2_bas_x'][i] ==0 and dayta['hour'][i] == 14 and dayta['val2_bas_y'][i]==1:
                bb.append('A414')
            elif dayta['val2_bas_x'][i] ==0 and dayta['hour'][i] == 15 and dayta['val2_bas_y'][i]==1:
                bb.append('A415')
            elif dayta['val2_bas_x'][i] ==0 and dayta['hour'][i] == 16 and dayta['val2_bas_y'][i]==1:
                bb.append('A416')
                
            elif dayta['val3_bas_x'][i] ==0 and dayta['hour'][i] == 16 and dayta['val3_bas_y'][i]==1:
                bb.append('A516')    
            elif dayta['val3_bas_x'][i] ==0 and dayta['hour'][i] == 17 and dayta['val3_bas_y'][i]==1:
                bb.append('A517')
            elif dayta['val3_bas_x'][i] ==0 and dayta['hour'][i] == 18 and dayta['val3_bas_y'][i]==1:
                bb.append('A518')
            else:
                bb.append('X')
        else:
            bb.append('X')
            
    dayta['val'] = bb
    
    #Exclude value contains L (Libur)
    gg = dayta[~dayta['val'].str.contains('X')]
    
    gg.reset_index()
    table2 = pd.pivot_table(gg, values=['val'], index=['agent'], columns=['day'],aggfunc=lambda x: ' '.join(x))
    
    table2.columns = table2.columns.droplevel(0)
    dfo = table2.reset_index().rename_axis(None, axis=1)
    
    dfo = dfo.replace(np.nan, 'X')
    
    return dfo

def cleaningText(text):
    text = re.sub(r'@[A-Za-z0-9]+', '', text) # remove mentions
    text = re.sub(r'#[A-Za-z0-9]+', '', text) # remove hashtag
    text = re.sub(r'RT[\s]', '', text) # remove RT
    text = re.sub(r"http\S+", '', text) # remove link
    text = re.sub(r'[0-9]+', '', text) # remove numbers
    text = text.replace('_', ' ') # replace new line into space
    return text

def repText(text):
    text = text.replace(' ', '_') # replace new line into space 
    return text

def str_func(Dt_bas, Dt__bas):
    Dt_bas['ag'] = Dt_bas['sh2_bas'].str.split('_').str[-1]
    Dt_bas['ag'] = Dt_bas['ag'].astype(int)
    Dt_bas['agent'] = Dt_bas['sh2_bas'].str[2:]
    Dt_bas['agent'] = Dt_bas['agent'].apply(cleaningText)
    Dt_bas['agent'] = Dt_bas['agent'].str.strip()
    Dt_bas['agent'] = Dt_bas['agent'].apply(repText)

    #in day
    Dt__bas['ag'] = Dt__bas['sh2_bas'].str.split('_').str[-1]
    Dt__bas['ag'] = Dt__bas['ag'].astype(int)
    Dt__bas['agent'] = Dt__bas['sh2_bas'].str[2:]
    Dt__bas['agent'] = Dt__bas['agent'].apply(cleaningText)
    Dt__bas['agent'] = Dt__bas['agent'].str.strip()
    Dt__bas['agent'] = Dt__bas['agent'].apply(repText)
    
    dt1 = result_basic(Dt_bas, Dt__bas)
    
    fg = []

    for i in dt1['agent']:
        fg.append(i.replace("_"," "))

    dt1['agent'] = fg

    yu = []

    for i in dt1['agent']:
        if i in df2_bas[df2_bas['role']=='Auditor']['agent_id'].to_list():
            yu.append('Auditor')
        else:
            yu.append('Agent')

    dt1.insert(loc=1, column='role', value=yu)

    # Translating X into reason based on df1_bas
    po = dt1['agent'].reset_index()
    for t in range(len(po)):
        for u in range(len(df1_bas)):
            if dt1['agent'][t] == df1_bas['name'][u]:
                dt1.loc[t,[x for x in range(df1_bas['daynum'][u],df1_bas['daynum'][u]+1)]] = df1_bas['reason'][u] 
    dt2 = dt1.copy()
    # Remove dates from previous month
    start_col = date1_next_month - last2_monday
    start_col = start_col.days
    start_col

    # Rename the column names
    dt2 = dt2.drop(dt2.columns[2:start_col+2], axis=1)
    now = datetime.now()
    next_month = now + relativedelta(months=+1)
    year = next_month.year
    month = next_month.month
    tot_days = monthrange(year, month)[1]
    col_name1 = ['agent','role']
    col_name = [str(i) for i in range(1,tot_days+1)]
    column_names = col_name1 + col_name
    dt2.columns = column_names      
    return dt2



date1_next_month,last2_monday,end_mo,end_mo2,num_days1,num_days2,delta_days = create_date()
dfdm = create_dfdm()
df = create_df(dfdm)
