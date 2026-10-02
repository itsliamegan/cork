from helios.view import Component

from app import Access, Archival, Preferences


class ArchivalItem(Component):
	template = "archivals.item"

	archival: Archival
	access: Access
	preferences: Preferences
