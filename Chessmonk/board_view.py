# Graphical display of a board, using a Board object as its model.

import gtk
import gtk.gdk
import gobject
import time
import copy
import cairo

from pieces import piece_surfaces
from square_utils import *
from board import Board
from utils import locate_data_dir

ANIMATION_TIME = 0.15
PADDING = 3	

class Piece:
	def _get_coords(self):
		return self._coords
	def _set_coords(self, value):
		self._coords = value
	coords = property(_get_coords, _set_coords)
	
	def _get_last_coords(self):
		return self._last_coords
	last_coords = property(_get_last_coords)
	
	def _get_square(self):
		return self._square
	square = property(_get_square)
	
	def _get_piece_id(self):
		return self._piece_id
	piece_id = property(_get_piece_id)
	
	def _get_opacity(self):
		return self._opacity
	opacity = property(_get_opacity)
	
	def get_dirty(self):
		return self._dirty
	def set_dirty(self, value):
		self._dirty = value
		
	def get_moving(self):
		return self._moving

	def __init__(self, square, piece_id):
		self._square = square
		self._piece_id = piece_id
		
		self._update_file_rank()
		
		# Coordinates in relative values (0.0 to 1.0)
		self._start = self._fyle * (1.0/8), self._rank * (1.0/8)
		self._destination = self._start
		self._coords = self._start
		
		self._start_opacity = 0.0
		self._destination_opacity = 1.0
		self._opacity = 0.0
		
		self._last_coords = self._start
		self._last_opacity = 0.0
		self._dirty = True
		self._moving = False
		
	def get_color(self):
		if (self._piece_id[0] == 'w'):
			return 'white'
		else:
			return 'black'
		
	def reset_start(self):
		self._start = self._coords
		self._start_opacity = self._opacity
	
	def update_for_alpha(self, alpha):
		self._last_coords = copy.copy(self._coords)
		self._last_opacity = copy.copy(self._opacity)
		
		(sx, sy) = self._start
		(dx, dy) = self._destination	
		self._coords = (sx+((dx-sx)*alpha), sy+((dy-sy)*alpha))
		
		(so, do) = self._start_opacity, self._destination_opacity
		self._opacity = so+((do-so)*alpha)
			
		if ( self._last_coords != self._coords or self._last_opacity != self._opacity ):
			self._dirty = True
		else:
			self._moving = False
		
	def set_opacity(self, opacity):
		self._start_opacity = self._opacity
		self._destination_opacity = opacity
		self._dirty = True
		
	def move_to(self, dest_square):
		self._destination = square_file(dest_square) * (1.0/8), square_rank(dest_square) * (1.0/8)
		self._square = dest_square
		self._destination_opacity = 1.0
		self._update_file_rank()
		self._moving = True
		self._dirty = True
		
	def move(self, x_offset, y_offset):
		x = self._start[0] + x_offset
		y = self._start[1] + y_offset
		#self._last_coords = self._coords
		#self._coords = (x, y)
		self._destination = (x, y)
		#self._dirty = True
		
	def _update_file_rank(self):
		self._fyle = square_file(self._square)
		self._rank = square_rank(self._square)	


class BoardView(gtk.DrawingArea):
	__gsignals__ = {
		"expose-event": "override",
		"motion-notify-event": "override",
		"button-press-event": "override",
		"button-release-event": "override",
	}
	
	
	def _get_board(self):
		return self._board
	board = property(_get_board)
	
	
	def __init__(self, boardwindow):
		gtk.DrawingArea.__init__(self)
		self.boardwindow = boardwindow
		self.set_events(gtk.gdk.SCROLL_MASK | 
		                gtk.gdk.POINTER_MOTION_MASK | 
		                gtk.gdk.BUTTON_PRESS_MASK |
		                gtk.gdk.BUTTON_RELEASE_MASK)
		
		self._board_size = 0
		self._board_offset = (0, 0)
		self._width = 360
		self._old_width = self._width
		self.set_size_request(self._width, self._width)
		
		self._flipped = False
		self._enable_animations = True
		self._draw_coordinates = True
		self._editable = True
		
		self._animation_timeout = None
		self._animation_scale = 1.0
		self._animation_time = time.time() + ANIMATION_TIME*self._animation_scale
		
		self._pieces = []
		self._piece_spool = []
		
		self._board_buffer = None
		self._buffer_size = (0, 0)
		self._draw_buffer = None
		self._dirty = False
		
		self._selected_piece = None
		self._selected_square = None
		self._prelight_square = None
		self._dragging = False
		self._drag_start = (0, 0)
		
		self._board = Board()
		self.update()
		
		self._board.connect('position-changed-event', self.position_changed_event)
		self.connect('scroll-event', self.scroll_event)
		
	
	def do_expose_event(self, event):
		self._resize()
		cr = self.window.cairo_create()
		cr.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
		cr.clip()
		self._prepare_context(cr, *self.window.get_size())
		self._draw(cr)
		
		
	def _run_animation(self):
		alpha = min(1.0, (time.time() - self._animation_time) / (ANIMATION_TIME*self._animation_scale))
		cr = self.window.cairo_create()
		self._prepare_context(cr, *self.window.get_size())
		self._draw(cr, redraw = False)
		
		if (alpha >= 1.0):
			return False
		return True
	
	
	def do_motion_notify_event(self, event):
		if (event.is_hint):
			(x, y, state) = event.window.get_pointer()
		else:
			x = event.x
			y = event.y
			state = event.state
		
		square = self._get_square_for_screen_coords((x, y))
		piece = self._get_piece_on_square(square)
		
		if (self._prelight_square != None):
			self._prelight_square = None
			self.queue_draw()
			
		if (self._selected_piece != None and self._dragging):
			newpos = self._screen_coords_to_relative((x, y))
			x_offset = newpos[0] - self._drag_start[0]
			y_offset = newpos[1] - self._drag_start[1]
			self._selected_piece.move(x_offset, y_offset)
			self.queue_draw()
			
		if (piece != None and piece.get_color() == self._board.side_to_move):
			# highlight current square if it contains a piece that can be moved
			self._prelight_square = square
			self.queue_draw()
			
		if (self._selected_square != None and (piece == None or piece.get_color() != self._board.side_to_move)):
			self._prelight_square = square
			self.queue_draw()
			
			
	def do_button_press_event(self, event):
		square = self._get_square_for_screen_coords(event.get_coords())
		piece = self._get_piece_on_square(square)
		
		if (self._selected_square != None):
			self._selected_square = None
			self._selected_piece = None
			self.queue_draw()
		
		if (piece != None and piece != self._selected_piece and piece.get_color() == self._board.side_to_move):
			square = self._get_square_for_screen_coords(event.get_coords())
			self._selected_square = square
			self._selected_piece = piece
			self._dragging = True
			self._drag_start = self._screen_coords_to_relative(event.get_coords())
			self.queue_draw()
		
		
	def do_button_release_event(self, event):
		square = self._get_square_for_screen_coords(event.get_coords())
		piece = self._get_piece_on_square(square)
		
		if (self._dragging):
			if (square != self._selected_square):
				print "move:", self._selected_square, square
				self._board.move_interactive(self._selected_square, square)
				self.update()
		
			self._dragging = False
			self._selected_piece.move(0, 0)
			self.queue_draw()
			

	def _get_square_for_screen_coords(self, coords):
		size = self._board_size
		borderpx = int(size*self._get_border_width())
		insize = size - borderpx * 2
		sw = int(insize / 8)
		
		x = (coords[0] - self._board_offset[0]) / sw
		y = (coords[1] - self._board_offset[1]) / sw
		
		if (x < 0 or y < 0 or x >= 8 or y >= 8):
			return None
		else:
			if (not self._flipped):
				y = 8 - y
			return (square_number(int(x), int(y)))

	
	def _screen_coords_to_relative(self, coords):
		size = self._board_size
		borderpx = int(size*self._get_border_width())
		insize = size - borderpx * 2
		
		x = (coords[0] - self._board_offset[0]) / insize
		y = (coords[1] - self._board_offset[1]) / insize
		
		if (not self._flipped):
			y = 1.0 - y
			
		x = min(1.0, x)
		x = max(0.0, x)
		y = min(1.0, y)
		y = max(0.0, y)
		
		return (x, y)
	
	def _square_to_coords(self, square):
		fyle = square_file(square)
		rank = square_rank(square)
		if (not self._flipped):
			rank = 7 - rank
		return fyle, rank
			
	
	def _get_border_width(self):
		if self._draw_coordinates:
			return 0.04
		else:
			return 0.02
			
	
	def _get_piece_on_square(self, square):
		for piece in self._pieces:
			if piece.square == square:
				return piece
		return None
		
		
	def _prepare_context(self, cr, width, height):
		size = min(width, height) - PADDING * 2
		borderpx = int(size*self._get_border_width())
		
		# Calculate sizes for an even square size for sharp intersections
		boardsize = size - (borderpx * 2)
		sw = int(boardsize / 8)
		boardsize = sw * 8
		size = boardsize + (borderpx * 2)
		
		self._board_size = size
		
		# Horizontally center the board
		cr.translate(int((width - (size + 2 * PADDING)) / 2), 0)
		cr.translate(PADDING, PADDING)
		
		self._board_offset = (int((width - (size + 2 * PADDING)) / 2 + borderpx + PADDING), int(borderpx + PADDING))
		
		return cr


	def _draw(self, cr, redraw = True):
		t1 = time.time()
		size = self._board_size
		borderpx = int(size*self._get_border_width())
		insize = size - borderpx * 2
		sw = int(insize / 8)
		
		self._draw_buffer = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
		draw_context = cairo.Context(self._draw_buffer)
		draw_context.set_line_width(1)
		
		# Create a new board when necessary
		if self._buffer_size != size or not self._board_buffer or self._dirty:
			self._board_buffer = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
			bc = cairo.Context(self._board_buffer)
			self._draw_board(bc)
			self._buffer_size = size
			self._dirty = False
		
        # Piece animation
		alpha = min(1.0, (time.time() - self._animation_time) / (ANIMATION_TIME*self._animation_scale))
		for piece in self._pieces:
			piece.update_for_alpha(alpha)
		
		if (redraw):
			draw_context.set_source_surface(self._board_buffer)
			draw_context.paint()
		else:
			# Redraw only damaged areas
			draw_context.set_source_surface(self._board_buffer)
			clip = False
			
			for piece in self._pieces:
				if (piece.get_dirty()):
					clip = True
					(x, y) = self._rotate_coordinates(piece.coords)
					cr.rectangle(insize*x+borderpx, insize*y+borderpx, sw, sw)
					(x, y) = self._rotate_coordinates(piece.last_coords)
					cr.rectangle(insize*x+borderpx, insize*y+borderpx, sw, sw)
					piece.set_dirty(False)
			# END for
			if (clip):
				cr.clip ()
			else:
				return	
			#return
			draw_context.set_source_surface(self._board_buffer)
			draw_context.paint()
		
		draw_context.translate(borderpx, borderpx)
		
		# Draw highlights
		if (self._prelight_square != None):
			(x, y) = self._square_to_coords(self._prelight_square)
			draw_context.set_source_rgba(0.9, 1, 0.9, 0.3)
			draw_context.rectangle(x*sw, y*sw, sw, sw)
			draw_context.fill()	
		if (self._selected_square != None):
			(x, y) = self._square_to_coords(self._selected_square)
			draw_context.set_source_rgba(0.9, 1, 0.7, 0.4)
			draw_context.rectangle(x*sw, y*sw, sw, sw)
			draw_context.fill()
        
        # Draw pieces
		for piece in self._pieces:
			#if ( not redraw and not piece._get_dirty() ):
			#	continue
			#else:
			#	piece._set_dirty(False)
			
			# Get rid of faded pieces
			if piece.square == -1 and piece.opacity <= 0:
				self._pieces.remove(piece)
				continue
			
			image = piece_surfaces[piece.piece_id]
			(x, y) = self._rotate_coordinates(piece.coords)
			draw_context.save()
			draw_context.rectangle(insize*x, insize*y, sw, sw)
			draw_context.clip()
			
			draw_context.translate(insize*x, insize*y)
			draw_context.scale(1.0*sw/image.get_width(), 1.0*sw/image.get_height())
			draw_context.set_source_surface(image, 0, 0)
			draw_context.paint_with_alpha(piece.opacity)
			draw_context.restore()
		# END for
		
		cr.set_source_surface(self._draw_buffer)
		cr.paint()
		
		#print "drawing time: " + str(time.time() - t1)
	# END _draw
	
	
	def _draw_board(self, cr):
		size = self._board_size
		borderpx = int(size*self._get_border_width())

		# Calculate sizes for an even square size for sharp intersections
		size = size - (borderpx * 2)
		sw = int(size / 8)
		size = sw * 8
		fullsize = size + (borderpx * 2)
		
		cr.set_line_width(1)
		
		cr.save()
		
		w = fullsize
		
		# Draw border background
		image = piece_surfaces['border']
		cr.rectangle(0, 0, w, w)
		cr.set_source_surface(image, 0, 0)
		pattern = cr.get_source()
		pattern.set_extend(cairo.EXTEND_REPEAT)
		cr.fill()
		
		# Draw outline
		cr.rectangle(0.5, 0.5, w-1, w-1)
		cr.set_source_rgb(0.2, 0.2, 0.2)
		cr.stroke()
		
		# Draw inside shadows
		cr.move_to(1.5, w-1.5)
		cr.line_to(1.5, 1.5)
		cr.line_to(w-1.5, 1.5)
		cr.set_source_rgba(1, 1, 1, 0.2)
		cr.stroke()
		cr.move_to(w-1.5, 1.5)
		cr.line_to(w-1.5, w-1.5)
		cr.line_to(1.5, w-1.5)
		cr.set_source_rgba(0, 0, 0, 0.3)
		cr.stroke()
		
		# Draw inside border
		cr.rectangle(borderpx-0.5, borderpx-0.5, w-2*borderpx+1, w-2*borderpx+1)
		cr.set_source_rgba(0, 0, 0, 0.2)
		cr.stroke()
			
		cr.translate(borderpx, borderpx)
		w = size
		
		# Draw Coordinates
		rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'] 
		lines = ['1', '2', '3', '4', '5', '6', '7', '8']
		if self._draw_coordinates:
			cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
			cr.set_font_size(borderpx*0.6)
			cr.set_source_rgba(1, 1, 1)
			cr.move_to(borderpx*0.2, borderpx*2)
			cr.show_text('A')
			
			if self._flipped:
				i = 7
			else:
				i = 0
			for row in rows:
				fw = cr.text_extents(row)[2]
				fh = cr.text_extents(row)[3]
				cr.move_to(sw*i + sw/2 - fw/2, w + borderpx*0.5 + fh/2)
				cr.show_text(row)
				if self._flipped:
					i -= 1
				else:
					i += 1
			# END for
				
			if self._flipped:
				i = 0
			else:
				i = 7
			for line in lines:
				fw = cr.text_extents(line)[2]
				fh = cr.text_extents(line)[3]
				cr.move_to(0-borderpx*0.55 - fw/2, sw*i + sw/2 + fh/2)
				cr.show_text(line)
				if self._flipped:
					i += 1
				else:
					i -= 1
			# END for
				
		# Draw the squares
		odd = True
		for i in range(8):
			for j in range(8):
				if odd:
					image = piece_surfaces['light-square']
					cr.save()
					cr.translate(sw*i, sw*j)
					cr.scale(1.0*sw/image.get_width(), 1.0*sw/image.get_height())
					cr.set_source_surface(image, 0, 0)
					cr.paint()
					cr.restore()
				else:
					image = piece_surfaces['dark-square']
					cr.save()
					cr.translate(sw*i, sw*j)
					cr.scale(1.0*sw/image.get_width(), 1.0*sw/image.get_height())
					cr.set_source_surface(image, 0, 0)
					cr.paint()
					cr.restore()
				odd = not odd
			odd = not odd
	# END _draw_board
			
		
	def update(self):	
		self._piece_spool = self._pieces
		self._pieces = []
		
		static_pieces = []
		moving_pieces = []
		
		for i in range(64):
			pi = self.board.get_square(i)
			if pi:
				piece = self._grab_piece(i, pi)
				
				# make sure moving pieces end up on top
				if ( piece.get_moving() ):
					moving_pieces.append(piece)
				else:
					static_pieces.append(piece)
					
		# Let the remaining pieces fade out
		for piece in self._piece_spool:
			piece.set_opacity(0.0)
			piece.square = -1
			self._pieces.append(piece)
			
		self._pieces += static_pieces + moving_pieces
			
		for piece in self._pieces:
			piece.reset_start()
			
		self._animation_time = time.time()
		self._animation_id = gobject.idle_add(self._run_animation)


	def _grab_piece(self, square, piece_id):
		"""Find a suitable piece or create a new one."""
		for piece in self._piece_spool:
			if piece.square == square and piece.piece_id == piece_id:
				self._piece_spool.remove(piece)
				return piece
				
		# Try to find a "free" piece of the same type and move it
		for piece in self._piece_spool:
			if piece.piece_id == piece_id and self._board.squares[piece.square] != piece_id and piece.square != -1:
				self._piece_spool.remove(piece)
				piece.move_to(square)
				return piece
		
		piece = Piece(square, piece_id)
		return piece

	def flip(self):
		self._flipped = not self._flipped
		self._prelight_square = None
		self._dirty = True
		self.queue_draw()
		
	def toggle_coordinates(self):
		self._draw_coordinates = not self._draw_coordinates
		self._dirty = True
		self.queue_draw()
		
	def save_png(self, filename):
		"""Draw the board view to a PNG surface and save it to filename."""
		image = cairo.ImageSurface(cairo.FORMAT_ARGB32, self._width, self._width)
		cr = cairo.Context(image)
		self._draw(cr, self._width, self._width)
		image.write_to_png(filename)
				

	def _calculate_width(self):
		wallocation = self.boardwindow.window.get_allocation()
		allocation = self.get_allocation()
		min_width = 160
		max_width = int(wallocation.height / 8) * 8 - 160
		width = int(allocation.width / 8) * 8
		return max(min(width, max_width), min_width) + 1

		
	def _resize(self):
		self._width = self._calculate_width()
		if self._width == self._old_width:
			return
		self.set_size_request(self._width, self._width)
		self._old_width = self._width
	
	
	# Return relative coordinates for piece drawing, depending on board rotation
	def _rotate_coordinates(self, coords):
		x, y = coords
		d = 1.0 / 8 * 7
		if self._flipped:
			return d - x, y
		else:
			return x, d - y


	def scroll_event(self, sender, event):
		# Yes this is opposite to how scid does it, but more intuitive
		if event.direction == gtk.gdk.SCROLL_DOWN:
			self._board.move_back()
		elif event.direction == gtk.gdk.SCROLL_UP:
			self._board.move_forward()

	
	def position_changed_event(self, sender, position):
		self.update()
	
