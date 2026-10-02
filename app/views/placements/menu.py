from helios.view import Component

from app import Access, Placement


class PlacementMenu(Component):
	template = "placements.menu"

	placement: Placement
	access: Access
