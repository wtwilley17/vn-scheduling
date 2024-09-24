import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
import pandas as pd
import csv
import io
import pulp 

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



