from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.data.store import NotFoundError, Store
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status, URL
from helios.views.engine import Views

from app.data import (
	Board,
	Pin,
	Placement,
	Share,
	User,
	find_accessible_board,
	find_accessible_pin,
	find_all_accessible_boards,
	find_contextual_placement,
	find_owned,
	find_pin_placements,
)


def _referring_board_id(
	raw_url: str | None,
	placements: list[Placement],
) -> UUID | None:
	if not isinstance(raw_url, str):
		return None
	try:
		path = URL(raw_url).path
	except ValueError:
		return None
	for placement in placements:
		if path == f"/boards/{placement.board_id}":
			return placement.board_id
	return None


def _pin_return_url(
	ctx: Context,
	raw_url: str | None,
	pin: Pin,
	placements: list[Placement],
) -> URL:
	fallback = URL(f"/pins/{pin.id}")
	if not isinstance(raw_url, str):
		return fallback
	try:
		path = URL(raw_url).path
	except ValueError:
		return fallback
	if path in {"/pins/", f"/pins/{pin.id}"}:
		return URL(path)
	board_id = _referring_board_id(raw_url, placements)
	if board_id is None:
		return fallback
	try:
		find_accessible_board(ctx, board_id)
	except NotFoundError:
		return fallback
	return URL(path)


def build_board_options(ctx: Context) -> list[dict[str, Board | str]]:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	boards = find_all_accessible_boards(ctx)
	board_ids = {board.id for board in boards}
	shares_by_board_id: dict[UUID, list[Share]] = {board.id: [] for board in boards}
	for share in store.find_all(Share):
		if share.board_id in board_ids:
			shares_by_board_id[share.board_id].append(share)

	viewer_ids = {board.creator_id for board in boards}
	viewer_ids.update(
		share.user_id for shares in shares_by_board_id.values() for share in shares
	)
	users_by_id = {
		user.id: user.name for user in store.find_all(User) if user.id in viewer_ids
	}
	board_options = []
	for board in boards:
		shares = shares_by_board_id[board.id]
		if not shares:
			sharing_label = "Private"
		else:
			visible_user_ids = {share.user_id for share in shares}
			if board.creator_id != auth.user.id:
				visible_user_ids.add(board.creator_id)
			visible_user_ids.discard(auth.user.id)
			viewer_names = sorted(
				(users_by_id[user_id] for user_id in visible_user_ids),
				key=str.casefold,
			)
			sharing_label = f"Shared · {", ".join(viewer_names)}"
		board_options.append({"board": board, "sharing_label": sharing_label})
	return board_options


def index(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	user = cast(User, auth.user)

	pins = store.find_by(Pin, creator_id=user.id)
	pins.sort(key=lambda pin: pin.created_at, reverse=True)
	pin_ids = {pin.id for pin in pins}
	placements_by_pin_id: dict[UUID, list[Placement]] = {pin.id: [] for pin in pins}
	for placement in store.find_all(Placement):
		if placement.pin_id in pin_ids:
			placements_by_pin_id[placement.pin_id].append(placement)
	pin_rows = []
	for pin in pins:
		pin_rows.append(
			{
				"pin": pin,
				"board_count": len(placements_by_pin_id[pin.id]),
			}
		)

	html = views.render(
		"pins.index",
		{
			"pin_rows": pin_rows,
			"current_user": user,
			"open_in_new_tab": user.open_in_new_tab,
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
			Field("url", parser.Required(parser.Str())),
			Field("note", parser.Optional(parser.Str())),
			Field("board_id", parser.List(parser.UUID())),
			Field("return_to", parser.Optional(parser.Str())),
		]
	)
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	board_ids = list(dict.fromkeys(input["board_id"]))
	try:
		boards = [find_accessible_board(ctx, board_id) for board_id in board_ids]
	except NotFoundError:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	pin = store.create(
		Pin,
		title=input["title"],
		url=input["url"],
		note=input["note"] or "",
		creator_id=user.id,
	)
	for board in boards:
		Placement.create(store, pin, board, user)

	return_to = URL("/pins/")
	if isinstance(input["return_to"], str):
		try:
			path = URL(input["return_to"]).path
		except ValueError:
			path = ""
		if path == "/pins/" or path in {f"/boards/{board.id}" for board in boards}:
			return_to = URL(path)
	return Response.redirect(return_to)


def render_new(ctx: Context, board: Board | None = None) -> Response:
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	return_to = URL(f"/boards/{board.id}") if board is not None else URL("/pins/")
	html = views.render(
		"pins.new",
		{
			"originating_board": board,
			"board_options": build_board_options(ctx),
			"selected_board_ids": {board.id} if board is not None else set(),
			"current_user": auth.user,
			"return_to": return_to,
		},
	)
	return Response.html(html)


def canonical_new(req: Request, ctx: Context) -> Response:
	return render_new(ctx)


def new(req: Request, ctx: Context, id: UUID) -> Response:
	return render_new(ctx, find_accessible_board(ctx, id))


def show(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	user = cast(User, auth.user)

	pin = find_accessible_pin(ctx, id)
	placements = find_pin_placements(store, pin.id)
	accessible_placements = []
	accessible_boards = []
	for placement in placements:
		try:
			board = find_accessible_board(ctx, placement.board_id)
		except NotFoundError:
			continue
		accessible_placements.append(placement)
		accessible_boards.append(board)
	contextual_placement = find_contextual_placement(
		accessible_placements, _referring_board_id(req.referrer, accessible_placements)
	)
	adder = (
		store.find_one(User, contextual_placement.adder_id)
		if contextual_placement is not None
		else None
	)
	html = views.render(
		"pins.show",
		{
			"pin": pin,
			"accessible_boards": accessible_boards,
			"creator": store.find_one(User, pin.creator_id),
			"adder": adder,
			"is_unfiled": not placements,
			"current_user": user,
			"open_in_new_tab": user.open_in_new_tab,
		},
	)
	return Response.html(html)


def edit(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)

	pin = find_owned(ctx, Pin, id)
	placements = find_pin_placements(store, pin.id)
	accessible_placements = []
	for placement in placements:
		try:
			find_accessible_board(ctx, placement.board_id)
		except NotFoundError:
			continue
		accessible_placements.append(placement)

	html = views.render(
		"pins.edit",
		{
			"pin": pin,
			"board_options": build_board_options(ctx),
			"selected_board_ids": {
				placement.board_id for placement in accessible_placements
			},
			"current_user": auth.user,
			"return_to": _pin_return_url(ctx, req.referrer, pin, placements),
		},
	)
	return Response.html(html)


def update(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)

	pin = find_owned(ctx, Pin, id)
	placements = find_pin_placements(store, pin.id)

	form = Form(
		[
			Field("url", parser.Required(parser.Str())),
			Field("title", parser.Required(parser.Str())),
			Field("board_id", parser.List(parser.UUID())),
			Field("note", parser.Optional(parser.Str())),
			Field("return_to", parser.Optional(parser.Str())),
		]
	)
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	board_ids = set(input["board_id"])
	try:
		boards_by_id = {
			board_id: find_accessible_board(ctx, board_id) for board_id in board_ids
		}
	except NotFoundError:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	return_to = _pin_return_url(ctx, input["return_to"], pin, placements)
	accessible_placements = []
	for placement in placements:
		try:
			find_accessible_board(ctx, placement.board_id)
		except NotFoundError:
			continue
		accessible_placements.append(placement)
	for placement in accessible_placements:
		if placement.board_id not in board_ids:
			store.delete(placement.id)
	existing_board_ids = {placement.board_id for placement in placements}
	for board_id in board_ids - existing_board_ids:
		Placement.create(store, pin, boards_by_id[board_id], user)
	pin.url = input["url"]
	pin.title = input["title"]
	pin.note = input["note"] or ""
	store.save(pin)

	return Response.redirect(return_to)


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)

	pin = find_owned(ctx, Pin, id)
	placements = find_pin_placements(store, pin.id)
	return_to = URL("/pins/")
	raw_return_to = req.input.items.get("return_to")
	if isinstance(raw_return_to, str):
		try:
			path = URL(raw_return_to).path
		except ValueError:
			path = ""
		if path == "/pins/":
			return_to = URL(path)
		else:
			board_id = _referring_board_id(raw_return_to, placements)
			if board_id is not None:
				try:
					find_accessible_board(ctx, board_id)
				except NotFoundError:
					pass
				else:
					return_to = URL(path)
	for placement in placements:
		store.delete(placement.id)
	store.delete(pin.id)

	return Response.redirect(return_to)
