from uuid import UUID

from helios.form import RuleError


class Distinct:
	name = "distinct"
	message = "must not repeat a value"

	def check(self, values: list[UUID]) -> list[UUID]:
		if len(set(values)) != len(values):
			raise RuleError()
		else:
			return values
