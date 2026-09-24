from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import NotFoundError, Store

from app.board import Board
from app.pin import Pin
from app.placement import Placement
from app.share import Share
from app.user import User


def find_owned[T: Pin | Board](ctx: Context, model_type: type[T], id: UUID) -> T:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)

	model = store.find_one(model_type, id)

	if model.creator_id != user.id:
		raise NotFoundError(model_type, id)
	return model


def find_pin_placements(store: Store, pin_id: UUID) -> list[Placement]:
	return store.find_by(Placement, pin_id=pin_id)


def find_contextual_placement(
	placements: list[Placement],
	board_id: UUID | None = None,
) -> Placement | None:
	if board_id is not None:
		for placement in placements:
			if placement.board_id == board_id:
				return placement
	if not placements:
		return None
	return min(placements, key=lambda placement: str(placement.id))


def can_remove_placement(
	ctx: Context,
	placement: Placement,
	pin: Pin,
	board: Board,
) -> bool:
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)
	return board.is_accessible(ctx) and user.id in {
		pin.creator_id,
		placement.adder_id,
		board.creator_id,
	}


def find_accessible_pin(ctx: Context, id: UUID) -> Pin:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)
	pin = store.find_one(Pin, id)
	if pin.creator_id == user.id:
		return pin
	board_ids = [placement.board_id for placement in find_pin_placements(store, pin.id)]
	owned_board = (
		store.query(Board).where_in(id=board_ids).where(creator_id=user.id).first()
	)
	share = (
		store.query(Share).where_in(board_id=board_ids).where(user_id=user.id).first()
	)
	if owned_board is None and share is None:
		raise NotFoundError(Pin, id)
	return pin
