from helios.view import Attributes, Component
from markupsafe import Markup


class ExternalLink(Component):
	template = "components.external_link"

	url: str
	new_tab: bool = False
	content: Markup = Markup("")
	attributes: Attributes = Attributes()
