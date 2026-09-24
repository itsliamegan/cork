from dataclasses import dataclass

from helios.view import Component


@dataclass
class ConfirmDialog(Component):
	template = "components.confirm_dialog"

	name: str
	action: str
	confirm: str
	content: str
	method: str | None = None
	required: bool = True

	@property
	def dialog_id(self) -> str:
		return f"{self.name}-dialog"

	@property
	def form_id(self) -> str:
		return f"{self.name}-form"
