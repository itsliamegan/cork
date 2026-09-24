from helios.view import Component

from app.views.boards.chip import BoardChip
from app.views.boards.chips import BoardChips
from app.views.components.action_menu import ActionMenu
from app.views.components.confirm_dialog import ConfirmDialog
from app.views.components.external_link import ExternalLink
from app.views.components.reorder_handle import ReorderHandle
from app.views.pins.details import PinDetails

components: list[type[Component]] = [
	ActionMenu,
	BoardChip,
	BoardChips,
	ConfirmDialog,
	ExternalLink,
	PinDetails,
	ReorderHandle,
]
