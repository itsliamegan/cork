from helios.view import Component

from app.views.archivals.item import ArchivalItem
from app.views.boards.chip import BoardChip
from app.views.boards.chips import BoardChips
from app.views.boards.item import BoardItem
from app.views.boards.sharing import BoardSharing
from app.views.components.action_menu import ActionMenu
from app.views.components.confirm_button import ConfirmButton
from app.views.components.external_link import ExternalLink
from app.views.pins.details import PinDetails
from app.views.pins.placements import PinPlacements
from app.views.placements.item import PlacementItem
from app.views.placements.menu import PlacementMenu

components: list[type[Component]] = [
	ActionMenu,
	ArchivalItem,
	BoardChip,
	BoardChips,
	BoardItem,
	BoardSharing,
	ConfirmButton,
	ExternalLink,
	PinDetails,
	PinPlacements,
	PlacementItem,
	PlacementMenu,
]
