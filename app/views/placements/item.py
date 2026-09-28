from helios.view import Component

from app import Access, Board, Pin, Placement, Preferences


class PlacementItem(Component):
	template = "placements.item"

	pin: Pin
	placement: Placement
	board: Board
	access: Access
	preferences: Preferences
