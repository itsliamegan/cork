from helios.view import Attributes, Component
from markupsafe import Markup

from app.views.components.confirm_dialog import ConfirmDialog


class ConfirmButton(Component):
	template = "components.confirm_button"

	name: str
	action: str
	confirm: str
	message: str
	method: str | None = None
	content: Markup = Markup("")
	attributes: Attributes = Attributes()

	@property
	def dialog(self) -> ConfirmDialog:
		return ConfirmDialog(
			name=self.name,
			action=self.action,
			confirm=self.confirm,
			content=self.message,
			method=self.method,
		)
