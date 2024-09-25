from ._anvil_designer import result_tableTemplate
from anvil import *
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from .. import global_var

class result_table(result_tableTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run before the form opens.

  def rich_text_1_show(self, **event_args):
    """This method is called when the RichText is shown on the screen"""
    self.rich_text_1.content = global_var.result

  def button_1_click(self, **event_args):
    """This method is called when the button is clicked"""
    csv = anvil.server.call('get_csv')
    download(csv)


