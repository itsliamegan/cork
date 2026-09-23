import helios.app
import helios.auth
import helios.database
import helios.flash
import helios.limit
from helios.routing import Router
import helios.session
from helios.session.file import Driver
import helios.views
from helios.wsgi import Application

from app.config import Config
from app.data import User, models
from app.http import routes


class Application(Application):
	def __init__(self, config: Config):
		super().__init__(
			helios.app.Config(base_url=config.base_url),
			Router(routes),
			[
				helios.views.Provider(config.views),
				helios.session.Provider(
					config.session,
					Driver(config.session_file, config.session_lock_file),
				),
				helios.database.Provider(config.database, models),
				helios.flash.Provider(),
				helios.auth.Provider(User),
			],
			[helios.limit.Middleware(config.rate_limit)],
		)
