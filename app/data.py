from datetime import datetime
from uuid import UUID

from helios.auth import Authenticator
from helios.data import Model, NotFoundError, Schema, Store, attr


class User(Model):
	name = attr(str)
	open_in_new_tab = attr(bool, default=False)


class Pin(Model):
	url = attr(str)
	title = attr(str)
	note = attr(str, default="")
	board_id = attr(UUID, nullable=True)
	user_id = attr(UUID)


class Board(Model):
	title = attr(str)
	user_id = attr(UUID)


class Share(Model):
	board_id = attr(UUID)
	user_id = attr(UUID)


class Ordering(Model):
	user_id = attr(UUID)
	board_id = attr(UUID)
	position = attr(int)


schema = Schema(
	[
		User,
		Pin,
		Board,
		Share,
		Ordering,
	]
)


def find_owned(ctx, model_type: type[Model], id: UUID) -> Model:
	model = ctx.get(Store).find_one(model_type, id)
	auth = ctx.get(Authenticator)
	if model.user_id != auth.user.id:
		raise NotFoundError(model_type, id)
	return model


def find_all_owned(ctx, model_type: type[Model], **attrs) -> list[Model]:
	auth = ctx.get(Authenticator)
	return ctx.get(Store).find_by(model_type, user_id=auth.user.id, **attrs)


def can_access_board(ctx, board: Board) -> bool:
	auth = ctx.get(Authenticator)
	if board.user_id == auth.user.id:
		return True
	return bool(ctx.get(Store).find_by(Share, board_id=board.id, user_id=auth.user.id))


def find_accessible_board(ctx, id: UUID) -> Board:
	board = ctx.get(Store).find_one(Board, id)
	if not can_access_board(ctx, board):
		raise NotFoundError(Board, id)
	return board


def find_accessible_pin(ctx, id: UUID) -> Pin:
	pin = ctx.get(Store).find_one(Pin, id)
	if pin.board_id is None:
		raise NotFoundError(Pin, id)
	try:
		find_accessible_board(ctx, pin.board_id)
	except NotFoundError as err:
		raise NotFoundError(Pin, id) from err
	return pin


def find_all_accessible_boards(ctx) -> list[Board]:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	shared_board_ids = {
		share.board_id for share in store.find_by(Share, user_id=auth.user.id)
	}
	return [
		board
		for board in store.find_all(Board)
		if board.user_id == auth.user.id or board.id in shared_board_ids
	]


def order_accessible_boards(ctx, boards: list[Board]) -> list[Board]:
	def created_at(board: Board) -> datetime:
		if board.created_at is None:
			raise ValueError("cannot order an unsaved board")
		return board.created_at

	board_ids = {board.id for board in boards}
	positions = {}
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	for ordering in store.find_by(Ordering, user_id=auth.user.id):
		if ordering.board_id not in board_ids:
			continue
		position = positions.get(ordering.board_id)
		if position is None or ordering.position < position:
			positions[ordering.board_id] = ordering.position

	unpositioned = sorted(
		(board for board in boards if board.id not in positions),
		key=created_at,
		reverse=True,
	)
	positioned = sorted(
		(board for board in boards if board.id in positions),
		key=created_at,
		reverse=True,
	)
	positioned.sort(key=lambda board: positions[board.id])

	return [*unpositioned, *positioned]
