from helios.database import Model


class User(Model):
	table = "users"

	name: str
	open_in_new_tab: bool = False
