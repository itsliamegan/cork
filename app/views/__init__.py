from helios.view import Component

from app.views.boards.chip import BoardChip
from app.views.boards.chips import BoardChips
from app.views.boards.item import BoardItem
from app.views.boards.sharing import BoardSharing
from app.views.components.action_menu import ActionMenu
from app.views.components.confirm_dialog import ConfirmDialog
from app.views.components.confirm_trigger import ConfirmTrigger
from app.views.components.external_link import ExternalLink
from app.views.pins.details import PinDetails
from app.views.pins.placements import PinPlacements

components: list[type[Component]] = [
	ActionMenu,
	BoardChip,
	BoardChips,
	BoardItem,
	BoardSharing,
	ConfirmDialog,
	ConfirmTrigger,
	ExternalLink,
	PinDetails,
	PinPlacements,
]
