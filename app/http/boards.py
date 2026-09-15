from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.data.store import Store
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status, URL
from helios.views.engine import Views

from app.data import (
	Board,
	Ordering,
	Pin,
	Placement,
	Share,
	User,
	can_remove_placement,
	find_accessible_board,
	find_all_accessible_boards,
	find_owned,
	order_accessible_boards,
)


def _board_return_url(raw_url: str | None, id: UUID) -> URL:
	fallback = URL(f"/boards/{id}")
	if not isinstance(raw_url, str):
		return fallback

	try:
		path = URL(raw_url).path
	except ValueError:
		return fallback

	if path == "/boards/" or path == f"/boards/{id}":
		return URL(path)
	return fallback


def _sharing_people(
	ctx: Context,
	owner_id: UUID,
	shared_user_ids: set[UUID] | None = None,
) -> list[dict]:
	store = ctx.get(Store)

	if shared_user_ids is None:
		shared_user_ids = set()
	users = [user for user in store.find_all(User) if user.id != owner_id]
	users.sort(key=lambda user: user.name.casefold())
	return [{"user": user, "has_access": user.id in shared_user_ids} for user in users]


def index(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	user = cast(User, auth.user)

	boards = order_accessible_boards(ctx, find_all_accessible_boards(ctx))
	shared_board_ids = {share.board_id for share in store.find_all(Share)}
	private_boards = [
		board
		for board in boards
		if board.creator_id == user.id and board.id not in shared_board_ids
	]
	shared_boards = [board for board in boards if board.id in shared_board_ids]

	html = views.render(
		"boards.index",
		{
			"private_boards": private_boards,
			"shared_boards": shared_boards,
			"current_user": auth.user,
		},
	)

	return Response.html(html)


def create(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
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
	available_user_ids = {
		available_user.id
		for available_user in store.find_all(User)
		if available_user.id != user.id
	}
	if not selected_user_ids <= available_user_ids:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	board = store.create(Board, title=input["title"], creator_id=user.id)
	for user_id in selected_user_ids:
		store.create(Share, board_id=board.id, user_id=user_id)

	return Response.redirect(URL(f"/boards/{board.id}"))


def new(req: Request, ctx: Context) -> Response:
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	user = cast(User, auth.user)

	html = views.render(
		"boards.new",
		{
			"current_user": auth.user,
			"owner": auth.user,
			"people": _sharing_people(ctx, user.id),
		},
	)
	return Response.html(html)


def show(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	user = cast(User, auth.user)

	board = find_accessible_board(ctx, id)
	placements = store.find_by(Placement, board_id=board.id)
	pin_rows = []
	for placement in placements:
		pin = store.find_one(Pin, placement.pin_id)
		pin_rows.append(
			{
				"placement": placement,
				"pin": pin,
				"can_remove": can_remove_placement(ctx, placement, pin, board),
			}
		)
	pin_rows.sort(key=lambda row: row["pin"].created_at, reverse=True)
	pin_rows.sort(key=lambda row: row["placement"].position)

	html = views.render(
		"boards.show",
		{
			"board": board,
			"pin_rows": pin_rows,
			"current_user": auth.user,
			"open_in_new_tab": user.open_in_new_tab,
		},
	)

	return Response.html(html)


def edit(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)

	board = find_owned(ctx, Board, id)
	shared_user_ids = {
		share.user_id for share in store.find_by(Share, board_id=board.id)
	}

	html = views.render(
		"boards.edit",
		{
			"board": board,
			"current_user": auth.user,
			"owner": auth.user,
			"people": _sharing_people(ctx, board.creator_id, shared_user_ids),
			"return_to": _board_return_url(req.referrer, board.id),
		},
	)

	return Response.html(html)


def update(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)

	board = find_owned(ctx, Board, id)
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

	available_user_ids = {
		user.id for user in store.find_all(User) if user.id != board.creator_id
	}
	if not selected_user_ids <= available_user_ids:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	shares = store.find_by(Share, board_id=board.id)
	shared_user_ids = {share.user_id for share in shares}
	for share in shares:
		if share.user_id not in selected_user_ids:
			store.delete(share.id)
	for user_id in selected_user_ids - shared_user_ids:
		store.create(Share, board_id=board.id, user_id=user_id)

	board.title = input["title"]
	store.save(board)

	return_to = _board_return_url(input["return_to"], board.id)
	return Response.redirect(return_to)


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)

	board = find_owned(ctx, Board, id)
	placements = store.find_by(Placement, board_id=board.id)
	shares = store.find_by(Share, board_id=board.id)
	orderings = store.find_by(Ordering, board_id=board.id)
	for placement in placements:
		store.delete(placement.id)
	for share in shares:
		store.delete(share.id)
	for ordering in orderings:
		store.delete(ordering.id)
	store.delete(board.id)

	return Response.redirect(URL("/boards/"))
