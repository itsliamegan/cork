from datetime import UTC, datetime, timedelta
import secrets
from uuid import UUID

from helios.database import Codec, Model, NotFoundError, Scalar, Store, belongs_to

from app.user import User


class Invite(Model):
	table = "invites"

	class Token:
		def __init__(self, value: str):
			self.value = value

		@classmethod
		def generate(cls) -> Invite.Token:
			return cls(secrets.token_urlsafe(32))

		class Codec(Codec):
			def check(self, value: object):
				if not isinstance(value, Invite.Token):
					raise TypeError(f"expected a Token, got {type(value).__name__}")

			def encode(self, value: Invite.Token) -> Scalar:
				self.check(value)
				return value.value

			def decode(self, value: Scalar) -> Invite.Token:
				if not isinstance(value, str):
					raise TypeError(f"expected a string, got {type(value).__name__}")
				return Invite.Token(value)

	token: Token
	creator_id: UUID
	creator: User = belongs_to("creator_id")
	target_id: UUID | None
	target: User | None = belongs_to("target_id")
	expires_at: datetime

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
		invite = store.query(cls).where({"token": cls.Token(token)}).first()
		if invite is None or invite.expires_at <= datetime.now(UTC):
			return None
		return invite

	@classmethod
	def find_created_by(cls, store: Store, id: UUID, creator: User) -> Invite:
		invite = store.find_one(cls, id)
		if invite.creator_id != creator.id:
			raise NotFoundError(cls, id)
		return invite

	def find_target(self, store: Store) -> User | None:
		if self.target_id is None:
			return None
		else:
			return store.find_one(User, self.target_id)

	def redeem(self, store: Store, name: str) -> User:
		if self.target_id is not None:
			raise ValueError(f"Invite {self.id} is for an existing user")
		user = store.create(User, name=name)
		store.delete(self)
		return user

	def redeem_for_target(self, store: Store) -> User:
		if self.target_id is None:
			raise ValueError(f"Invite {self.id} has no target")
		user = store.find_one(User, self.target_id)
		store.delete(self)
		return user
