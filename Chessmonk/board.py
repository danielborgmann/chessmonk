import gobject
from copy import deepcopy

from node import Node
from square_utils import *
from position import Position

class Board(gobject.GObject):
	__gsignals__ = {
		'position-changed-event' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
		#'move-event' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
    }

	def __init__(self, position=None):
		gobject.GObject.__init__(self)
		
		self.history = None
		
		if position:
			self.set_position(position)
		else:
			self.setup_starting_pieces()
	
	def get_square(self, square):
		return self.position.squares[square]	
		
	def set_game(self, game):
		self.history = game.notation.nodes
		self.set_position(game.notation.nodes[0].position)
		
	# Update each square to match the given position 
	def set_position(self, position):
		self.position = position
		self.fullmove_number = position.fullmove_number
		self.side_to_move = position.side_to_move
		self.en_passant_file = position.en_passant_file
		self.en_passant_square = position.en_passant_square
		self.castling_availability = position.castling_availability
		self.halfmove_clock = position.halfmove_clock
		for i in range(64):
			if self.squares[i] != position.squares[i]:
				self.squares[i] = position.squares[i]
		self.emit('position-changed-event', position)

	def copy_position(self):
		return copy.deepcopy(self.position)
				
	def load_node(self, node):
		self.node = node
		self.set_position(node.position)
			
	# Find the square of the piece which may move to target (if any)
	def find_move(self, piece_index, target, capture, ax, ay):
		if self.position.side_to_move == "white":
			piece_type = "w"
		else:
			piece_type = "b"
		piece_type += piece_index.lower()
		
		for i in range(64):
			if self.squares[i] == piece_type:
				if ax > -1 and square_file(i) != ax:
					continue
				if ay > -1 and square_rank(i) != ay: 
					continue
				if self.check_legal_move(piece_index, i, target, capture):
					return i
					
		return None
	
	# Check a move for legality
	# piece_index: The algebraic notation of the piece type
	# square: The square from which the piece will move
	# target: The square to which the piece will move			
	def check_legal_move(self, piece_index, square, target, capture):
		direction = square_direction(square, target)
		distance = square_distance(square, target)
		
		if piece_index == "P" and not capture:
			if self.side_to_move == "white":
				if direction != "N": return False
				# Allow double-move from second rank
				if square_rank(square) == 1:
					if distance > 2: return False
					if distance == 2 and self.squares[square_shift(square, direction)]: return False
				else:
					if distance > 1: return False
			else:
				if direction != "S": return False
				# Allow double-move from seventh rank
				if square_rank(square) == 6:
					if distance > 2: return False
					if distance == 2 and self.squares[square_shift(square, direction)]: return False
				else:
					if distance > 1: return False
		else:
			if not self.square_can_attack(square, target, piece_index): return False				
		
		# Make sure the king is not left in check. This could probably be a little more elegant...
		testPosition = self.get_position()
		testPosition.squares[square] = ""
		if self.side_to_move == "white":
			testPosition.squares[target] = "w" + piece_index.lower()
			testPosition.side_to_move = "black"
		else:
			testPosition.squares[target] = "b" + piece_index.lower()
			testPosition.side_to_move = "white"
		return testPosition.is_legal()
	
	def setup_starting_pieces(self):
		self.position = Position()
		for i in range(8):
			self.position.squares[i+8] = "wp"
			self.position.squares[i+48] = "bp"
		self.position.squares[sq("a1")] = "wr"
		self.position.squares[sq("h1")] = "wr"
		self.position.squares[sq("b1")] = "wn"
		self.position.squares[sq("g1")] = "wn"
		self.position.squares[sq("c1")] = "wb"
		self.position.squares[sq("f1")] = "wb"
		self.position.squares[sq("d1")] = "wq"
		self.position.squares[sq("e1")] = "wk"
		self.position.squares[sq("a8")] = "br"
		self.position.squares[sq("h8")] = "br"
		self.position.squares[sq("b8")] = "bn"
		self.position.squares[sq("g8")] = "bn"
		self.position.squares[sq("c8")] = "bb"
		self.position.squares[sq("f8")] = "bb"
		self.position.squares[sq("d8")] = "bq"
		self.position.squares[sq("e8")] = "bk"
		
	def reset(self):
		self.squares = []
		for i in range(64):
			self.squares.append("")
		self.set_position(self.node.position)
		
	def move_interactive(self, square, target, variation = False, promo_piece = ""):
		piece = self.squares[square]
		capture_piece = self.squares[target]	
		capture = capture_piece != None
		
		board = Board(position=self.get_position())
		board.add_move(square, target, piece, capture, promo_piece)
		node = Node()
		move = {}
		move["square"] = square
		move["target"] = target
		node.movelist.append(move)
		node.position = board.get_position()
		node.previous = self.node
		self.node.next = node
		self.move_forward()
	
	def add_move(self, square, target, pieceLetter, capture, promoPieceLetter):
		fyle = square_file(square)
		rank = square_rank(square)
		target_file = square_file(target)
		target_rank = square_rank(target)
		
		if self.side_to_move == "black": self.fullmove_number += 1
		
		# Check for en passant capture
		self.en_passant_square = None
		if self.en_passant_file and capture and pieceLetter == "P" and target_file == self.en_passant_file:
			if self.side_to_move == "white" and target_rank == 5:
				self.squares[square_number(target_file, 4)] = ""
				self.en_passant_square = square_number(target_file, 4)
			elif self.side_to_move == "black" and target_rank == 2:
				self.squares[square_number(target_file, 3)] = ""
				self.en_passant_square = square_number(target_file, 3)
		
		# Update en passant file
		self.en_passant_file = None
		if pieceLetter == "P":
			if self.side_to_move == "white" and rank == 1 and target_rank == 3:
				self.en_passant_file = target_file
			if self.side_to_move == "black" and rank == 6 and target_rank == 4:
				self.en_passant_file = target_file
				
		# Update castling availability
		no_castle = []
		if pieceLetter == 'K':
			no_castle.append('K')
			no_castle.append('Q')
		if pieceLetter == 'R':
			if fyle == 0:
				no_castle.append('Q')
			else:
				no_castle.append('K')
		if self.side_to_move == "black":
			for i in range(len(no_castle)):
				no_castle[i] = no_castle[i].lower()
		for x in no_castle:
			try:
				self.castling_availability.remove(x)
			except ValueError:
				pass
		
		# Update halfmove clock
		if capture or pieceLetter == 'P':
			self.halfmove_clock = 0
		else:
			self.halfmove_clock += 1
		
		if promoPieceLetter:
			if self.side_to_move == "white":
				self.squares[target] = "w" + promoPieceLetter.lower()
			else:
				self.squares[target] = "b" + promoPieceLetter.lower()
		else:
			self.squares[target] = self.squares[square]
		self.squares[square] = ""
		
	def swap_color(self):
		if self.side_to_move == "white":
			self.side_to_move = "black"
		else:
			self.side_to_move = "white"
			
	def move_forward(self):
		if not self.node.next: return
	
		self.node = self.node.next
		self.set_position(self.node.position)
	
	def move_back(self):
		if not self.node.previous: return
	
		self.node = self.node.previous
		self.set_position(self.node.position)
		
	def move_first(self):
		while self.node.previous: self.node = self.node.previous
		self.set_position(self.node.position)
	
	def move_last(self):
		while self.node.next: self.node = self.node.next
		self.set_position(self.node.position)	
			
	def castle_kingside(self):
		if self.side_to_move == "black": x = 56
		else: x = 0
		self.add_move(4+x, 6+x, "K", False, None)
		self.add_move(7+x, 5+x, "R", False, None)
	
	def castle_queenside(self):
		if self.side_to_move == "black": x = 56
		else: x = 0
		self.add_move(4+x, 2+x, "K", False, None)
		self.add_move(0+x, 3+x, "R", False, None)
# END class

		