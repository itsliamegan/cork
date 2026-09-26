from typing import TYPE_CHECKING
from uuid import UUID

from helios.database import Model, Store
from helios.http import URL

from app.placement import Placement

if TYPE_CHECKING:
	from app.access import Access
	from app.board import Board


class Pin(Model):
	table = "pins"

	url: str
	title: str
	note: str = ""
	creator_id: UUID

	def find_placements(
		self,
		store: Store,
		access: Access | None = None,
	) -> list[Placement]:
		placements = store.find_by(Placement, pin_id=self.id)
		if access is None:
			return placements
		board_ids = access.find_board_ids()
		return [
			placement for placement in placements if placement.board_id in board_ids
		]

	def place_on(self, store: Store, boards: list[Board], access: Access) -> None:
		chosen_board_ids = {board.id for board in boards}
		inaccessible_board_ids = chosen_board_ids - access.find_board_ids()
		if inaccessible_board_ids:
			raise ValueError(f"Boards {inaccessible_board_ids} are not accessible")

		for placement in self.find_placements(store, access):
			if placement.board_id not in chosen_board_ids:
				store.delete(placement)
		placed_board_ids = {
			placement.board_id for placement in self.find_placements(store)
		}
		for board in boards:
			if board.id not in placed_board_ids:
				Placement.create(store, self, board, access.user)
				placed_board_ids.add(board.id)

	def display_url(self) -> str:
		try:
			host = URL(self.url).host
		except ValueError:
			return self.url
		return host.removeprefix("www.") if host else self.url
