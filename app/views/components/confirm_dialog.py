from dataclasses import dataclass

from helios.view import Component
from markupsafe import Markup


@dataclass
class ConfirmDialog(Component):
	template = "components.confirm_dialog"

	name: str
	action: str
	confirm: str
	content: Markup
	method: str | None = None
