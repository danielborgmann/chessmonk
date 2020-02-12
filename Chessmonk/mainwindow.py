# coding: utf-8

import os
import sys

import gtk
import gtk.glade

import utils
import PGN
from board_view import BoardView
from notation_view import NotationView
from gamelist import GameList
from ECO import ECO

class MainWindow:
	def __init__(self, app):
		self.app = app
		self.filename = ""
	
		widgets = gtk.glade.XML(utils.locate_data_dir() + "chessmonk.glade")
		widgets.signal_autoconnect(self)
		
		self.window = widgets.get_widget("mainwindow")
		self.boardbox = widgets.get_widget("alignment_board_display")
		self.hpane = widgets.get_widget("hpane")
		self.vpane = widgets.get_widget("vpane")
		
		self.hpane.set_position(380)
		self.vpane.set_position(150)
		
		self.window.set_size_request(800, 600)
		
		try:
			icon = gtk.icon_theme_get_default().load_icon("chessmonk", 48, 0)
			self.window.set_icon(icon)
		except:
			print "Warning:", sys.exc_info()[1]
					
		# Move control buttons
		self.button_move_first = widgets.get_widget("button_move_first")
		self.button_move_back = widgets.get_widget("button_move_back")
		self.button_move_takeback = widgets.get_widget("button_move_takeback")
		self.button_move_forward = widgets.get_widget("button_move_forward")
		self.button_move_last = widgets.get_widget("button_move_last")
		
		from gtkboardview.BoardView import *
		self.boardview = BoardView()
		#self.board = self.boardview.board
		self.boardbox.add(self.boardview)
		
		self.boardview.board.connect('position-changed-event', self.position_changed_event)
		
		self.notationview = NotationView()
		self.notationview.board = self.boardview.board
		self.boardview.board.connect('position-changed-event', self.notationview.position_changed_event) 
		widgets.get_widget('sw_notation').add(self.notationview)
		
		self.gamelist = GameList(self)
				
		#self.notebook = gtk.Notebook()
		#widgets.get_widget("notebook_box").add(self.notebook)
		#self.notebook.append_page(self.gamelist)
		widgets.get_widget("sw_gamelist").add(self.gamelist)
		
		self.window.show_all()		
		self.button_move_takeback.hide() # TODO: reconsider
		
	def on_resize(self, widget):
		#self.boardview.on_resize()
		pass
		
	def on_rotate(self, widget):
		self.boardview.flip()
		
	def on_show_coordinates_toggle(self, widget):
		self.boardview.toggle_coordinates()
	
	def on_button_move_back_clicked(self, widget):
		self.boardview.board.move_back()
	
	def on_button_move_forward_clicked(self, widget):
		self.boardview.board.move_forward()
		
	def on_button_move_first_clicked(self, widget):
		self.boardview.board.move_first()
	
	def on_button_move_last_clicked(self, widget):
		self.boardview.board.move_last()
		
	def open_game(self, game):
		#game.notation.nodes = PGN.parse_string(game.notation_string)
		from gtkboardview import PGNfeeder
		PGNfeeder.feed(self.boardview.board, game.notation_string)
		#self.boardview.board.set_game(game)
		#self.boardview.update()
		self.notationview.update()
		
	def load_games(self, filename):
		self.gamelist.load(filename)
		self.open_game(self.gamelist.games[0])
		self.filename = filename
		filebase = os.path.splitext(os.path.basename(filename))[0]
		self.window.set_title(filebase)
		
	def on_open(self, sender):
		fc = gtk.FileChooserDialog(title="Open", parent=self.window,
		                           buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
		                                    gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT))
		if self.filename:
			fc.set_filename(self.filename)
		result = fc.run()
		fc.hide()
		if result == gtk.RESPONSE_ACCEPT:
			self.load_games(fc.get_filename())
			
	def on_save_board_image(self, sender):
		fc = gtk.FileChooserDialog(title="Save Image", parent=self.window,
		                           action=gtk.FILE_CHOOSER_ACTION_SAVE,
		                           buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
		                                    gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT))
		result = fc.run()
		fc.hide()
		if result == gtk.RESPONSE_ACCEPT:
			self.boardview.save_png(fc.get_filename())
			
	def on_about(self, sender):
		ad = gtk.AboutDialog()
		ad.set_name("Chessmonk")
		ad.set_comments("Open Source Chess Viewer and Database Tool")
		ad.set_version(utils.get_version())
		ad.set_copyright("Copyright © 2006 Daniel Borgmann")
		ad.set_authors([
			"Daniel Borgmann <daniel.borgmann@gmail.com>",
			"Nils R Grotnes <nils.grotnes@gmail.com>",
		])
		ad.set_license(utils.get_license())
		ad.set_logo_icon_name("chessmonk")
		ad.run()
		
	def on_close(self, sender=None, event=None):
		gtk.main_quit()
			
	def position_changed_event(self, sender, new_position=None):
		print self.app.eco.get_name(new_position.get_FEN())
	
