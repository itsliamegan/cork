from uuid import UUID

from helios.database import Model, attr


class Share(Model):
	table = "shares"

	board_id = attr(UUID)
	user_id = attr(UUID)
