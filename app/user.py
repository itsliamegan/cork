from helios.database import Model, attr


class User(Model):
	table = "users"

	name = attr(str)
	open_in_new_tab = attr(bool, default=False)
