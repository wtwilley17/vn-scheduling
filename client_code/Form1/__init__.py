from ._anvil_designer import Form1Template
from anvil import *
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from .. import global_var
from datetime import datetime

holiday = []
holiday_msg = ''

class Form1(Form1Template):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    # Any code you write here will run before the form opens.

  def date_picker_1_change(self, **event_args):
    """This method is called when the selected date changes"""
    pass

  def button_3_click(self, **event_args):
    """This method is called when the button is clicked"""
    file = self.file_loader_2.file
    anvil.server.call('store_agent_data',file)
    self.agent_data_repeating.items = app_tables.agent_data.search()

  def button_4_click(self, **event_args):
    """This method is called when the button is clicked"""
    file = self.file_loader_1.file
    anvil.server.call('store_leave_data',file)
    self.agent_leave_repeating.items = app_tables.agent_leave.search()


  def add_holiday_click(self, **event_args):
    """This method is called when the button is clicked"""
    global holiday
    global holiday_msg
    add_date = self.holiday_date.date
    if add_date == None:
      alert('Cant Insert Empty Value')
      return
    holiday.append(add_date)
    holiday_msg = ''
    for i in holiday:
      holiday_msg += f'{i} \n'
    self.holiday_text.text = holiday_msg

  def reset_holiday_click(self, **event_args):
    """This method is called when the button is clicked"""
    global holiday
    global holiday_msg
    holiday = []
    holiday_msg = ''
    self.holiday_text.text = holiday_msg

  def submit_holiday_click(self, **event_args):
    """This method is called when the button is clicked"""
    global holiday
    anvil.server.call('submit_holiday',holiday)
    
    
    


