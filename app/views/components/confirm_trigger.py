from dataclasses import dataclass

from helios.view import Attributes, Component
from markupsafe import Markup

from app.views.components.confirm_dialog import ConfirmDialog


@dataclass
class ConfirmTrigger(Component):
	template = "components.confirm_trigger"

	dialog: ConfirmDialog
	content: Markup = Markup("")
	attributes: Attributes = Attributes()
