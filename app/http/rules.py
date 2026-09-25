from uuid import UUID

from helios.form import Rule, RuleError


class Distinct(Rule[list[UUID], list[UUID]]):
	name = "distinct"
	message = "must not repeat a value"

	def check(self, value: list[UUID]) -> list[UUID]:
		if len(set(value)) != len(value):
			raise RuleError()
		return value
