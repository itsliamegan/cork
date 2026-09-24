from dataclasses import dataclass

from helios.view import Component
from markupsafe import Markup


@dataclass
class ActionMenu(Component):
	template = "components.action_menu"

	name: str
	content: Markup
