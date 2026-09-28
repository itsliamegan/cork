from helios.view import Component

from app import Access, Archival, Board, Pin, Placement, Preferences


class ArchivalItem(Component):
	template = "archivals.item"

	archival: Archival
	pin: Pin
	placement: Placement
	board: Board
	access: Access
	preferences: Preferences
