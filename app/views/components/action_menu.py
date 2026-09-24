from helios.view import Component
from markupsafe import Markup


class ActionMenu(Component):
	template = "components.action_menu"

	name: str
	content: Markup
