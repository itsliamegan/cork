from uuid import UUID

from helios.database import Model


class Share(Model):
	table = "shares"

	board_id: UUID
	user_id: UUID
