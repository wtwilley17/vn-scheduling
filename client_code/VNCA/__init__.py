from ._anvil_designer import VNCATemplate
from anvil import *
import anvil.users
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.server
from .. import global_var
from datetime import datetime
from ..result_table import result_table

holiday = []
holiday_msg = ''

class VNCA(VNCATemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.result = ''
    #self.repeating_panel_get_leave.items = anvil.server.call('get_agent_leave_pg')
    # Any code you write here will run before the form opens.
  
  def upload_agent_click(self, **event_args):
    """This method is called when the button is clicked"""
    file = self.file_loader_2.file
    if file == None:
      alert('Please Upload Agent List')
    else:
      anvil.server.call('store_agent_data',file)
      self.agent_data_repeating.items = app_tables.agent_list.search()

  def upload_leave_click(self, **event_args):
    """This method is called when the button is clicked"""
    file = self.file_loader_1.file
    if file == None:
      alert('Please Upload Agent Leave')
    else:
      anvil.server.call('store_leave_data',file)
      self.agent_leave_repeating.items = app_tables.agent_leave.search()
      anvil.server.call('store_df1bas')

  def add_holiday_click(self, **event_args):
    """This method is called when the button is clicked"""
    global holiday,holiday_msg
    add_date = self.holiday_date.date
    if add_date == None:
      alert('Cant Insert Empty Value')
      return
    holiday.append(add_date)
    holiday_msg = ''
    for i in holiday:
      holiday_msg += f'{i} \n'
    self.holiday_text.text = holiday_msg
    self.holiday_date.date = ''
    
  def reset_holiday_click(self, **event_args):
    """This method is called when the button is clicked"""
    global holiday
    global holiday_msg
    holiday = []
    holiday_msg = ''
    self.holiday_text.text = holiday_msg

  # def submit_holiday_click(self, **event_args):
  #   """This method is called when the button is clicked"""
  #   global holiday
  #   anvil.server.call('submit_holiday',holiday)

  def create_schedule_click(self, **event_args):
    """This method is called when the button is clicked"""
    a1 = self.text_box_1.text
    a2 = self.text_box_2.text
    a5 = self.text_box_3.text
    global_var.result, supply, demand = anvil.server.call('scheduling',holiday,a1,a2,a5)
    if global_var.result == 'Infeasible':
      error_mes = f'{global_var.result} \nShift Supply : {supply} \nShift Demand : {demand}'
      alert(error_mes,large=True)
    else:
      self.card_5.visible = True
      self.final_table.visible = True
      self.download_result.visible = True
      self.final_table.content = global_var.result
      alert(content=result_table(),
        title="VNCA Schedule Result",
        large=True,)

  def download_result_click(self, **event_args):
    """This method is called when the button is clicked"""
    csv = anvil.server.call('get_csv')
    download(csv)

  def holiday_date_show(self, **event_args):
    """This method is called when the DatePicker is shown on the screen"""
    self.holiday_date.min_date = global_var.next_month_first
    self.holiday_date.max_date = global_var.next_month_last

  def link_1_click(self, **event_args):
    """This method is called when the link is clicked"""
    open_form('VNCA.VNCA')

  def link_2_click(self, **event_args):
    """This method is called when the link is clicked"""
    open_form('VNCA.guideform')

  def text_box_1_show(self, **event_args):
    """This method is called when the TextBox is shown on the screen"""
    self.text_box_1.text = 1

  def text_box_2_show(self, **event_args):
    """This method is called when the TextBox is shown on the screen"""
    self.text_box_2.text = 1

  def text_box_3_show(self, **event_args):
    """This method is called when the TextBox is shown on the screen"""
    self.text_box_3.text = 2


    
    
    


