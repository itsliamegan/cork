from helios.view import Component

from app import Access, Placement, Preferences


class PlacementItem(Component):
	template = "placements.item"

	placement: Placement
	access: Access
	preferences: Preferences
