from typing import Any, cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status, URL
from helios.routing import URLs
from helios.view import Views

from app import Access, Board, Ordering, Pin, Placement, Removal, Share, User


def _board_return_url(ctx: Context, raw_url: str | None, id: UUID) -> URL:
	urls = ctx.get(URLs)
	match = urls.match(raw_url)
	if match is not None and match.route.name == "boards.index":
		return urls.route("boards.index")
	else:
		return urls.route("boards.show", {"id": id})


def _sharable_users(ctx: Context, owner_id: UUID) -> list[User]:
	store = ctx.get(Store)

	users = [user for user in store.find_all(User) if user.id != owner_id]
	users.sort(key=lambda user: user.name.casefold())
	return users


def _are_sharable_users(store: Store, user_ids: set[UUID], owner_id: UUID) -> bool:
	if owner_id in user_ids:
		return False
	users = store.query(User).where_in(id=user_ids).all()
	return len(users) == len(user_ids)


def index(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	user = cast(User, auth.user)
	access = Access(ctx)

	boards = Ordering.arrange(ctx, access.find_boards())
	shared_board_ids = {
		share.board_id
		for share in store.query(Share)
		.where_in(board_id=[board.id for board in boards])
		.all()
	}
	private_boards = [
		board
		for board in boards
		if board.creator_id == user.id and board.id not in shared_board_ids
	]
	shared_boards = [board for board in boards if board.id in shared_board_ids]

	return views.render(
		"boards.index",
		{
			"private_boards": private_boards,
			"shared_boards": shared_boards,
		},
	)


def create(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	form = Form(
		[
			Field("title", parser.Required(parser.Str())),
			Field("user_id", parser.List(parser.UUID())),
		]
	)
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	selected_user_ids = set(input["user_id"])
	if not _are_sharable_users(store, selected_user_ids, user.id):
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	board = store.create(Board, title=input["title"], creator_id=user.id)
	for user_id in selected_user_ids:
		store.create(Share, board_id=board.id, user_id=user_id)

	return Response.redirect(urls.route("boards.show", {"id": board.id}))


def new(req: Request, ctx: Context) -> Response:
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	user = cast(User, auth.user)

	return views.render(
		"boards.new",
		{
			"owner": auth.user,
			"users": _sharable_users(ctx, user.id),
			"shared_user_ids": set(),
		},
	)


def show(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	views = ctx.get(Views)
	access = Access(ctx)

	board = access.find_board(id)
	placements = store.find_by(Placement, board_id=board.id)
	pin_ids = [placement.pin_id for placement in placements]
	pins_by_id = {pin.id: pin for pin in store.query(Pin).where_in(id=pin_ids).all()}
	pin_rows: list[dict[str, Any]] = []
	for placement in placements:
		pin = pins_by_id[placement.pin_id]
		pin_rows.append(
			{
				"placement": placement,
				"pin": pin,
				"can_remove": Removal(placement, pin, board).is_authorized(ctx),
			}
		)
	pin_rows.sort(key=lambda row: row["pin"].created_at, reverse=True)
	pin_rows.sort(key=lambda row: row["placement"].position)

	return views.render(
		"boards.show",
		{
			"board": board,
			"pin_rows": pin_rows,
		},
	)


def edit(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)

	board = Board.find_owned(ctx, id)
	shared_user_ids = {
		share.user_id for share in store.find_by(Share, board_id=board.id)
	}

	return views.render(
		"boards.edit",
		{
			"board": board,
			"owner": auth.user,
			"users": _sharable_users(ctx, board.creator_id),
			"shared_user_ids": shared_user_ids,
			"return_to": _board_return_url(ctx, req.referrer, board.id),
		},
	)


def update(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)

	board = Board.find_owned(ctx, id)
	form = Form(
		[
			Field("title", parser.Required(parser.Str())),
			Field("user_id", parser.List(parser.UUID())),
			Field("return_to", parser.Optional(parser.Str())),
		]
	)
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	selected_user_ids = set(input["user_id"])
	if not _are_sharable_users(store, selected_user_ids, board.creator_id):
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	shares = store.find_by(Share, board_id=board.id)
	shared_user_ids = {share.user_id for share in shares}
	for share in shares:
		if share.user_id not in selected_user_ids:
			store.delete(share)
	for user_id in selected_user_ids - shared_user_ids:
		store.create(Share, board_id=board.id, user_id=user_id)

	board.title = input["title"]
	store.save(board)

	return_to = _board_return_url(ctx, input["return_to"], board.id)
	return Response.redirect(return_to)


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	urls = ctx.get(URLs)

	board = Board.find_owned(ctx, id)
	store.delete(board)

	return Response.redirect(urls.route("boards.index"))
