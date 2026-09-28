from helios.database import Model

from app.preferences import Preferences


class User(Model):
	table = "users"

	name: str
	open_in_new_tab: bool = False

	@property
	def preferences(self) -> Preferences:
		return Preferences(open_in_new_tab=self.open_in_new_tab)
