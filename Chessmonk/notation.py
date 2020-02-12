# A notation holds an array of node objects (whoops, where has all the code gone :D)

from board import Board
from node import Node
import PGN

class Notation:
	def __init__(self, string=None):
		self.nodes = []
		if string: self.nodes = PGN.parse_string(string)
