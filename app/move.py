from dataclasses import dataclass
from uuid import UUID


class OutOfDate(Exception):
	"""The mover's view of the order no longer matches the stored one."""


@dataclass
class Move:
	record_id: UUID
	above_id: UUID | None
	below_id: UUID | None

	def apply(self, record_ids: list[UUID]) -> list[UUID] | None:
		for id in (self.record_id, self.above_id, self.below_id):
			if id is not None and id not in record_ids:
				raise OutOfDate(f"{id} is not in the order")

		start = -1 if self.above_id is None else record_ids.index(self.above_id)
		end = (
			len(record_ids)
			if self.below_id is None
			else record_ids.index(self.below_id)
		)
		if start > end:
			raise OutOfDate(f"{self.above_id} comes after {self.below_id}")
		between = record_ids[start + 1 : end]
		if any(id != self.record_id for id in between):
			raise OutOfDate(
				f"Other records lie between {self.above_id} and {self.below_id}"
			)
		if self.record_id in between:
			return None

		moved = [id for id in record_ids if id != self.record_id]
		if self.above_id is None:
			return [self.record_id, *moved]
		elif self.below_id is None:
			return [*moved, self.record_id]
		else:
			index = moved.index(self.above_id) + 1
			return [*moved[:index], self.record_id, *moved[index:]]
