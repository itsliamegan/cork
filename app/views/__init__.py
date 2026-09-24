from helios.view import Component

from app.views.boards.chip import BoardChip
from app.views.boards.chips import BoardChips
from app.views.components.external_link import ExternalLink

components: list[type[Component]] = [
	BoardChip,
	BoardChips,
	ExternalLink,
]
