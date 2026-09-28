from helios.view import Component, Markup


class ActionMenu(Component):
	template = "components.action_menu"

	name: str
	content: Markup
