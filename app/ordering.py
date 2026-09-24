from uuid import UUID

from helios.database import Model, attr


class Ordering(Model):
	table = "orderings"

	user_id = attr(UUID)
	board_id = attr(UUID)
	position = attr(int)
