import gtk
import PGN

class GameList(gtk.TreeView):
	def __init__(self, window):
		self.parent_window = window
		self.games = []
	
		gtk.TreeView.__init__(self)
		
		self.connect("row-activated", self.on_row_activated)
		
		self.set_rules_hint(True)
		self.set_enable_search(False)
		
		self.store = gtk.ListStore(int, str, str, str, str, str)
		self.set_model(self.store)
		
		column_white = gtk.TreeViewColumn('White')
		column_white.set_resizable(True)
		column_black = gtk.TreeViewColumn('Black')
		column_black.set_resizable(True)
		column_white_elo = gtk.TreeViewColumn('Elo')
		column_white_elo.set_resizable(True)
		column_black_elo = gtk.TreeViewColumn('Elo')
		column_black_elo.set_resizable(True)
		column_result = gtk.TreeViewColumn('Result')
		column_result.set_resizable(True)
		
		self.append_column(column_white)
		self.append_column(column_white_elo)
		self.append_column(column_black)
		self.append_column(column_black_elo)
		self.append_column(column_result)
		
		cell = gtk.CellRendererText()
		column_white.pack_start(cell, True)
		column_white.add_attribute(cell, 'text', 1)
		column_white_elo.pack_start(cell, True)
		column_white_elo.add_attribute(cell, 'text', 2)
		column_black.pack_start(cell, True)
		column_black.add_attribute(cell, 'text', 3)
		column_black_elo.pack_start(cell, True)
		column_black_elo.add_attribute(cell, 'text', 4)
		column_result.pack_start(cell, True)
		column_result.add_attribute(cell, 'text', 5)
		
	def load(self, filename):
		self.store.clear()
		for game in PGN.parse(filename):
			self.games.append(game)
			self.store.append([game.index, 
			                   game.keys['White'], game.keys['WhiteElo'], 
			                   game.keys['Black'], game.keys['BlackElo'], 
			                   game.keys['Result']])
		
		self.set_cursor(0)
		self.columns_autosize()
		
	def on_row_activated(self, widget, path, col):
		self.parent_window.open_game(self.games[self.store[path][0]])
		
