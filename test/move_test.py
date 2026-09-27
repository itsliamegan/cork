from uuid import uuid4

from luna.test.assertion import assert_eq, assert_raises, assert_that

from app import Move
from app.move import OutOfDate


def test_a_record_missing_from_the_order_is_out_of_date():
	first, second = uuid4(), uuid4()

	with assert_raises(OutOfDate):
		Move(uuid4(), first, second).apply([first, second])


def test_a_neighbour_missing_from_the_order_is_out_of_date():
	first, second = uuid4(), uuid4()

	with assert_raises(OutOfDate):
		Move(first, uuid4(), None).apply([first, second])
	with assert_raises(OutOfDate):
		Move(first, None, uuid4()).apply([first, second])


def test_neighbours_in_reverse_order_are_out_of_date():
	first, second, third = uuid4(), uuid4(), uuid4()

	with assert_raises(OutOfDate):
		Move(first, third, second).apply([first, second, third])


def test_another_record_between_the_neighbours_is_out_of_date():
	first, second, third, fourth = uuid4(), uuid4(), uuid4(), uuid4()

	with assert_raises(OutOfDate):
		Move(fourth, first, third).apply([first, second, third, fourth])


def test_another_record_before_the_first_neighbour_is_out_of_date():
	first, second, third = uuid4(), uuid4(), uuid4()

	with assert_raises(OutOfDate):
		Move(third, None, second).apply([first, second, third])


def test_another_record_after_the_last_neighbour_is_out_of_date():
	first, second, third = uuid4(), uuid4(), uuid4()

	with assert_raises(OutOfDate):
		Move(first, second, None).apply([first, second, third])


def test_a_record_already_between_its_neighbours_is_a_no_op():
	first, second, third = uuid4(), uuid4(), uuid4()

	order = Move(second, first, third).apply([first, second, third])

	assert_that(order is None)


def test_a_record_without_a_neighbour_above_moves_first():
	first, second, third = uuid4(), uuid4(), uuid4()

	order = Move(third, None, first).apply([first, second, third])

	assert_eq(order, [third, first, second])


def test_a_record_without_a_neighbour_below_moves_last():
	first, second, third = uuid4(), uuid4(), uuid4()

	order = Move(first, third, None).apply([first, second, third])

	assert_eq(order, [second, third, first])


def test_a_record_between_neighbours_moves_directly_after_the_one_above():
	first, second, third, fourth = uuid4(), uuid4(), uuid4(), uuid4()

	order = Move(fourth, first, second).apply([first, second, third, fourth])

	assert_eq(order, [first, fourth, second, third])
