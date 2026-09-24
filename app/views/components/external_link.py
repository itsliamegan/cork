from dataclasses import dataclass

from helios.view import Attributes, Component
from markupsafe import Markup


@dataclass
class ExternalLink(Component):
	template = "components.external_link"
	accepts = {"target", "rel"}

	url: str
	new_tab: bool = False
	content: Markup = Markup("")
	attributes: Attributes = Attributes()
