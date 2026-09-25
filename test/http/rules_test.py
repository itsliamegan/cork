from uuid import uuid4

from helios.form import RuleError
from luna.test.assertion import assert_eq, assert_raises

from app.http.rules import Distinct


def test_distinct_passes_unique_values_through_in_order():
	first, second, third = uuid4(), uuid4(), uuid4()

	checked = Distinct().check([third, first, second])

	assert_eq(checked, [third, first, second])


def test_distinct_accepts_an_empty_list():
	assert_eq(Distinct().check([]), [])


def test_distinct_rejects_a_repeated_value():
	repeated = uuid4()

	with assert_raises(RuleError):
		Distinct().check([repeated, uuid4(), repeated])
