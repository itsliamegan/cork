from helios.view import Attributes, Component
from markupsafe import Markup

from app import Pin


class PinLink(Component):
	template = "pins.link"

	pin: Pin
	new_tab: bool = False
	content: Markup = Markup("")
	attributes: Attributes = Attributes()
