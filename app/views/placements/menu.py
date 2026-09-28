from helios.view import Component

from app import Access, Board, Pin, Placement


class PlacementMenu(Component):
	template = "placements.menu"

	pin: Pin
	placement: Placement
	board: Board
	access: Access
