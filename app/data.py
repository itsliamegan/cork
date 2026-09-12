from datetime import UTC, datetime, timedelta
import secrets
from uuid import UUID

from helios.auth import Authenticator
from helios.auth.password import Digest
from helios.data.model import Model, attr
from helios.data.store import NotFoundError, Schema, Store


class InvalidInviteError(ValueError):
	pass


class User(Model):
	name = attr(str)
	open_in_new_tab = attr(bool, default=False)

	@classmethod
	def recover(cls, store: Store, code: str) -> tuple[User, Recovery] | None:
		recovery = Recovery.find_by_code(store, code)
		if recovery is None:
			return None
		try:
			user = store.find_one(cls, recovery.user_id)
		except NotFoundError:
			return None
		new_recovery = Recovery.create(store, user)
		return user, new_recovery


class Recovery(Model):
	class Code:
		ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
		LENGTH = 16

		def __init__(self, digest: Digest, plaintext: str | None = None):
			self.digest = digest
			self.plaintext = plaintext

		@classmethod
		def generate(cls) -> Recovery.Code:
			plaintext = "".join(secrets.choice(cls.ALPHABET) for _ in range(cls.LENGTH))
			return cls(Digest.generate(plaintext), plaintext)

		def matches(self, candidate: str) -> bool:
			return self.digest.matches(candidate)

		@classmethod
		def check(cls, val: object):
			if not isinstance(val, cls):
				raise TypeError(f"expected a Code, got {type(val).__name__}")

		@classmethod
		def encode(cls, val: Recovery.Code) -> str:
			cls.check(val)
			return val.digest.encode()

		@classmethod
		def decode(cls, val: object) -> Recovery.Code:
			if not isinstance(val, str):
				raise TypeError(f"expected a string, got {type(val).__name__}")
			return cls(Digest.decode(val))

	user_id = attr(UUID)
	code = attr(Code)

	@classmethod
	def create(cls, store: Store, user: User) -> Recovery:
		code = cls.Code.generate()
		while cls.find_by_code(store, code.plaintext) is not None:
			code = cls.Code.generate()
		for recovery in store.find_by(cls, user_id=user.id):
			store.delete(recovery.id)
		return store.create(
			cls,
			user_id=user.id,
			code=code,
		)

	@classmethod
	def find_by_code(cls, store: Store, code: str) -> Recovery | None:
		for recovery in store.find_all(cls):
			if recovery.code.matches(code):
				return recovery
		return None

	@classmethod
	def find_owned(cls, store: Store, id: UUID, user: User) -> Recovery:
		recovery = store.find_one(cls, id)
		if recovery.user_id != user.id:
			raise NotFoundError(cls, id)
		return recovery

	@classmethod
	def exists_for(cls, store: Store, user: User) -> bool:
		return bool(store.find_by(cls, user_id=user.id))


class Invite(Model):
	class Token:
		def __init__(self, value: str):
			self.value = value

		@classmethod
		def generate(cls) -> Invite.Token:
			return cls(secrets.token_urlsafe(32))

		@classmethod
		def check(cls, val: object):
			if not isinstance(val, cls):
				raise TypeError(f"expected a Token, got {type(val).__name__}")

		@classmethod
		def encode(cls, val: Invite.Token) -> str:
			cls.check(val)
			return val.value

		@classmethod
		def decode(cls, val: object) -> Invite.Token:
			if not isinstance(val, str):
				raise TypeError(f"expected a string, got {type(val).__name__}")
			return cls(val)

	token = attr(Token)
	creator_id = attr(UUID)
	target_id = attr(UUID, nullable=True)
	expires_at = attr(datetime)

	@classmethod
	def create(
		cls,
		store: Store,
		creator: User,
		*,
		target: User | None = None,
	) -> Invite:
		token = cls.Token.generate()
		duration = timedelta(hours=24) if target is not None else timedelta(days=7)
		expires_at = datetime.now(UTC) + duration
		return store.create(
			cls,
			token=token,
			creator_id=creator.id,
			target_id=target.id if target is not None else None,
			expires_at=expires_at,
		)

	@classmethod
	def find_valid(cls, store: Store, token: str) -> Invite | None:
		for invite in store.find_all(cls):
			if invite.token.value == token:
				if invite.expires_at <= datetime.now(UTC):
					return None
				return invite
		return None

	@classmethod
	def find_created_by(cls, store: Store, id: UUID, creator: User) -> Invite:
		invite = store.find_one(cls, id)
		if invite.creator_id != creator.id:
			raise NotFoundError(cls, id)
		return invite

	def find_target(self, store: Store) -> User | None:
		if self.target_id is None:
			return None
		try:
			return store.find_one(User, self.target_id)
		except NotFoundError as error:
			raise InvalidInviteError from error

	def redeem(self, store: Store, name: str) -> User:
		target = self.find_target(store)
		if target is not None:
			store.delete(self.id)
			return target

		user = store.create(User, name=name)
		store.delete(self.id)
		return user


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
		Recovery,
		Invite,
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
