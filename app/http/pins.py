from urllib.parse import urlsplit
from uuid import UUID

from helios.app import Context
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status, URL

from app.data import (
	Board,
	Pin,
	User,
	find_accessible_board,
	find_accessible_pin,
	find_all_accessible_boards,
	find_owned,
)


def _pin_return_url(raw_url: str | None, pin: Pin) -> URL:
	fallback = URL(f"/pins/{pin.id}")
	if not isinstance(raw_url, str):
		return fallback

	try:
		path = urlsplit(raw_url).path
	except ValueError:
		return fallback

	if path == f"/pins/{pin.id}":
		return URL(path)
	if pin.board_id is not None and path == f"/boards/{pin.board_id}":
		return URL(path)
	return fallback


def create(req: Request, ctx: Context) -> Response:
	form = Form(
		[
			Field("title", parser.Required(parser.Str())),
			Field("url", parser.Required(parser.Str())),
			Field("note", parser.Str()),
			Field("board_id", parser.Required(parser.UUID())),
		]
	)
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	board = find_accessible_board(ctx, input["board_id"])

	ctx.store.create(
		Pin,
		title=input["title"],
		url=input["url"],
		note=input["note"],
		board_id=board.id,
		user_id=ctx.auth.user.id,
	)

	return Response.redirect(URL(f"/boards/{board.id}"))


def new(req: Request, ctx: Context, id: UUID) -> Response:
	board_id = id
	board = find_accessible_board(ctx, board_id)
	boards = find_all_accessible_boards(ctx)
	html = ctx.views.render(
		"pins.new",
		{
			"board": board,
			"board_id": board_id,
			"boards": boards,
			"current_user": ctx.auth.user,
		},
	)
	return Response.html(html)


def show(req: Request, ctx: Context, id: UUID) -> Response:
	pin = find_accessible_pin(ctx, id)
	board = find_accessible_board(ctx, pin.board_id)
	creator = ctx.store.find_one(User, pin.user_id)
	html = ctx.views.render(
		"pins.show",
		{
			"pin": pin,
			"board": board,
			"creator": creator,
			"current_user": ctx.auth.user,
			"open_in_new_tab": ctx.auth.user.open_in_new_tab,
		},
	)
	return Response.html(html)


def edit(req: Request, ctx: Context, id: UUID) -> Response:
	pin = find_owned(ctx, Pin, id)
	board = ctx.store.find_one(Board, pin.board_id) if pin.board_id else None
	boards = find_all_accessible_boards(ctx)
	html = ctx.views.render(
		"pins.edit",
		{
			"pin": pin,
			"board": board,
			"boards": boards,
			"current_user": ctx.auth.user,
			"return_to": _pin_return_url(req.referrer, pin),
		},
	)
	return Response.html(html)


def update(req: Request, ctx: Context, id: UUID) -> Response:
	pin = find_owned(ctx, Pin, id)

	form = Form(
		[
			Field("url", parser.Required(parser.Str())),
			Field("title", parser.Required(parser.Str())),
			Field("board_id", parser.Required(parser.UUID())),
			Field("note", parser.Optional(parser.Str())),
			Field("return_to", parser.Optional(parser.Str())),
		]
	)
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	board = find_accessible_board(ctx, input["board_id"])
	return_to = _pin_return_url(input["return_to"], pin)

	pin.url = input["url"]
	pin.title = input["title"]
	pin.board_id = board.id
	pin.note = input["note"] or ""
	ctx.store.save(pin)

	return Response.redirect(return_to)


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	pin = find_owned(ctx, Pin, id)

	if pin.board_id is None:
		board_url = URL("/")
	else:
		board_url = URL(f"/boards/{pin.board_id}")

	ctx.store.delete(pin.id)

	return Response.redirect(board_url)
