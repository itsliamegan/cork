from uuid import UUID

from helios.database import Model, attr


class Board(Model):
	table = "boards"

	title = attr(str)
	creator_id = attr(UUID)
