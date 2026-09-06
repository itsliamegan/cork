from app.data import find_all_accessible_boards, find_accessible_board, find_owned, Board, Pin, Share, User

from helios.app import Context
from helios.forms import rules, Field, Form
from helios.http import Request, Response, Status, URL

from uuid import UUID

def index(req: Request, ctx: Context) -> Response:
	boards = find_all_accessible_boards(ctx)

	html = ctx.views.render("boards.index", {
		"boards": boards,
		"current_user_id": ctx.auth.user.id,
	})

	return Response.html(html)

def create(req: Request, ctx: Context) -> Response:
	form = Form([
		Field("title", [rules.required])
	])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)

	board = ctx.store.create(Board, title = input["title"], user_id = ctx.auth.user.id)

	return Response.redirect(URL(f"/boards/{board.id}"))

def new(req: Request, ctx: Context) -> Response:
	html = ctx.views.render("boards.new")
	return Response.html(html)

def show(req: Request, ctx: Context, id: UUID) -> Response:
	board = find_accessible_board(ctx, id)
	pins = ctx.store.find_by(Pin, board_id = board.id)

	html = ctx.views.render("boards.show", {
		"board": board,
		"pins": pins,
		"current_user_id": ctx.auth.user.id,
	})

	return Response.html(html)

def edit(req: Request, ctx: Context, id: UUID) -> Response:
	board = find_owned(ctx, Board, id)
	shared_user_ids = {
		share.user_id
		for share in ctx.store.find_by(Share, board_id = board.id)
	}
	users = [
		user
		for user in ctx.store.find_all(User)
		if user.id != board.user_id
	]
	users.sort(key = lambda user: user.name.casefold())
	people = [
		{"user": user, "has_access": user.id in shared_user_ids}
		for user in users
	]

	html = ctx.views.render("boards.edit", {
		"board": board,
		"owner": ctx.auth.user,
		"people": people,
	})

	return Response.html(html)

def update(req: Request, ctx: Context, id: UUID) -> Response:
	board = find_owned(ctx, Board, id)
	form = Form([
		Field("title", [rules.required])
	])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)

	raw_user_ids = req.input["user_id"] if "user_id" in req.input else []
	if isinstance(raw_user_ids, str):
		raw_user_ids = [raw_user_ids]
	try:
		selected_user_ids = {UUID(raw_user_id) for raw_user_id in raw_user_ids}
	except (AttributeError, TypeError, ValueError):
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)

	available_user_ids = {
		user.id
		for user in ctx.store.find_all(User)
		if user.id != board.user_id
	}
	if not selected_user_ids <= available_user_ids:
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)

	shares = ctx.store.find_by(Share, board_id = board.id)
	shared_user_ids = {share.user_id for share in shares}
	for share in shares:
		if share.user_id not in selected_user_ids:
			ctx.store.delete(Share, share.id)
	for user_id in selected_user_ids - shared_user_ids:
		ctx.store.create(Share, board_id = board.id, user_id = user_id)

	board.title = input["title"]
	return Response.redirect(URL("/boards/"))

def delete(req: Request, ctx: Context, id: UUID) -> Response:
	board = find_owned(ctx, Board, id)
	pins = ctx.store.find_by(Pin, board_id = board.id)
	shares = ctx.store.find_by(Share, board_id = board.id)
	for pin in pins:
		ctx.store.delete(Pin, pin.id)
	for share in shares:
		ctx.store.delete(Share, share.id)
	ctx.store.delete(Board, board.id)

	return Response.redirect(URL("/boards/"))
