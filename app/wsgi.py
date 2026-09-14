import helios.app
import helios.auth
import helios.data
import helios.flash
import helios.limit
import helios.persist
from helios.persist.files import Files
from helios.routing import Router
import helios.session
import helios.views
from helios.wsgi import Application

from app.config import Config
from app.data import User, schema
from app.http import routes


class Application(Application):
	def __init__(self, config: Config):
		files = Files(config.persist)
		super().__init__(
			helios.app.Config(base_url=config.base_url),
			Router(routes),
			[
				helios.persist.Provider(files),
				helios.data.Provider(config.data, files, schema),
				helios.views.Provider(config.views),
				helios.session.Provider(config.session, files),
				helios.flash.Provider(),
				helios.auth.Provider(User),
			],
			[helios.limit.Middleware(config.rate_limit)],
		)
