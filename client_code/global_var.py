import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
# This is a module.
# You can define variables and functions here, and use them from any form. For example, in a top-level form:
#
#    from . import Module1
#
#    Module1.say_hello()
#

from datetime import datetime,timedelta
from calendar import monthrange


result = ''
now = datetime.now()
next_month = now + timedelta(28)
year = next_month.year
month = next_month.month
tot_days = monthrange(year, month)[1]
col_name1 = ['agent','role']
col_name = [str(i) for i in range(1,tot_days+1)]
column_names = col_name1 + col_name

next_month_first = f'{year}-{month}-01'
next_month_last = f'{year}-{month}-{tot_days}'