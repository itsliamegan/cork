from uuid import UUID

from app.data import Board, Share, User, find_owned

from helios.app import Context
from helios.forms import rules, Field, Form
from helios.http import Request, Response, URL
from helios.store import NotFoundError


def index(req: Request, ctx: Context, id: UUID) -> Response:
	board = find_owned(ctx, Board, id)

	shares = ctx.store.find_by(Share, board_id = board.id)
	recipients = []
	shared_user_ids = set()
	for share in shares:
		try:
			user = ctx.store.find_one(User, share.user_id)
		except NotFoundError:
			continue
		recipients.append({"share": share, "user": user})
		shared_user_ids.add(user.id)

	candidates = [
		user for user in ctx.store.find_all(User)
		if user.id != board.user_id and user.id not in shared_user_ids
	]
	recipients.sort(key = lambda recipient: recipient["user"].name.casefold())
	candidates.sort(key = lambda user: user.name.casefold())
	error = ctx.flash["error"] if "error" in ctx.flash else None

	html = ctx.views.render("boards.shares", {
		"board": board,
		"owner": ctx.auth.user,
		"recipients": recipients,
		"candidates": candidates,
		"error": error,
	})
	return Response.html(html)


def create(req: Request, ctx: Context, id: UUID) -> Response:
	board = find_owned(ctx, Board, id)

	form = Form([
		Field("user_id", [rules.required]),
	])
	input, errs = form.validate(req.input)
	if errs:
		ctx.flash["error"] = "Choose a person to share this board with."
		return Response.redirect(URL(f"/boards/{board.id}/shares"))

	try:
		user_id = UUID(input["user_id"])
		user = ctx.store.find_one(User, user_id)
	except (TypeError, ValueError, NotFoundError):
		ctx.flash["error"] = "That user does not exist."
		return Response.redirect(URL(f"/boards/{board.id}/shares"))
	if user.id == board.user_id:
		ctx.flash["error"] = "You already own this board."
		return Response.redirect(URL(f"/boards/{board.id}/shares"))

	existing = ctx.store.find_by(Share, board_id = board.id, user_id = user.id)
	if existing:
		ctx.flash["error"] = "That user already has access."
		return Response.redirect(URL(f"/boards/{board.id}/shares"))

	ctx.store.create(Share, board_id = board.id, user_id = user.id)
	return Response.redirect(URL(f"/boards/{board.id}/shares"))


def delete(req: Request, ctx: Context, id: UUID, share_id: UUID) -> Response:
	board = find_owned(ctx, Board, id)

	share = ctx.store.find_one(Share, share_id)
	if share.board_id != board.id:
		raise NotFoundError(Share, share.id)

	ctx.store.delete(Share, share.id)
	return Response.redirect(URL(f"/boards/{board.id}/shares"))
