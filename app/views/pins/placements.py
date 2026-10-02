from helios.view import Component

from app import Board, User


class PinPlacements(Component):
	template = "pins.placements"

	boards: list[Board]
	viewer: User
	selected_board_ids: set[str]

	def others(self, board: Board) -> list[User]:
		return [member for member in board.members() if member.id != self.viewer.id]
