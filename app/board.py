from uuid import UUID

from helios.database import Model


class Board(Model):
	table = "boards"

	title: str
	creator_id: UUID
