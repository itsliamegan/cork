from uuid import UUID as Id

from helios.store import Attribute, Model, NotFoundError, Schema, types


class User(Model):
	attrs = [
		Attribute("name", types.Str()),
		Attribute("open_in_new_tab", types.Bool(), default=False),
	]


class Pin(Model):
	attrs = [
		Attribute("url", types.Str()),
		Attribute("title", types.Str()),
		Attribute("note", types.Str(), default=""),
		Attribute("board_id", types.UUID(), nullable=True),
		Attribute("user_id", types.UUID()),
	]


class Board(Model):
	attrs = [
		Attribute("title", types.Str()),
		Attribute("user_id", types.UUID()),
	]


class Share(Model):
	attrs = [
		Attribute("board_id", types.UUID()),
		Attribute("user_id", types.UUID()),
	]


schema = Schema(
	[
		User,
		Pin,
		Board,
		Share,
	]
)


def find_owned(ctx, model_type: type[Model], id: Id) -> Model:
	model = ctx.store.find_one(model_type, id)
	if model.user_id != ctx.auth.user.id:
		raise NotFoundError(model_type, id)
	return model


def find_all_owned(ctx, model_type: type[Model], **attrs) -> list[Model]:
	return ctx.store.find_by(model_type, user_id=ctx.auth.user.id, **attrs)


def can_access_board(ctx, board: Board) -> bool:
	if board.user_id == ctx.auth.user.id:
		return True
	return bool(ctx.store.find_by(Share, board_id=board.id, user_id=ctx.auth.user.id))


def find_accessible_board(ctx, id: Id) -> Board:
	board = ctx.store.find_one(Board, id)
	if not can_access_board(ctx, board):
		raise NotFoundError(Board, id)
	return board


def find_accessible_pin(ctx, id: Id) -> Pin:
	pin = ctx.store.find_one(Pin, id)
	if pin.board_id is None:
		raise NotFoundError(Pin, id)
	try:
		find_accessible_board(ctx, pin.board_id)
	except NotFoundError as err:
		raise NotFoundError(Pin, id) from err
	return pin


def find_all_accessible_boards(ctx) -> list[Board]:
	shared_board_ids = {
		share.board_id for share in ctx.store.find_by(Share, user_id=ctx.auth.user.id)
	}
	return [
		board
		for board in ctx.store.find_all(Board)
		if board.user_id == ctx.auth.user.id or board.id in shared_board_ids
	]
