from app.access import Access
from app.board import Board
from app.pin import Pin
from app.placement import Placement


class Removal:
	def __init__(self, placement: Placement, pin: Pin, board: Board):
		self.placement = placement
		self.pin = pin
		self.board = board

	def is_authorized(self, access: Access) -> bool:
		return access.allows_board(self.board) and (
			access.ownership.owns(self.pin)
			or access.ownership.owns(self.board)
			or self.placement.adder_id == access.user.id
		)
