import helios.assets.provider
import helios.auth
from helios.config import Environment
import helios.database.provider
import helios.form
from helios.http import Status
import helios.limit
from helios.routing import Router
import helios.session
import helios.view.provider
from helios.wsgi import Application

from app import User, config, registry
from app.access import NotPermitted
from app.http import routes
from app.views import components, helpers


class Application(Application):
	def __init__(self, environment: Environment):
		super().__init__(
			config.application(environment),
			Router(routes),
			[
				helios.assets.provider.Provider(config.assets(environment)),
				helios.view.provider.Provider(
					config.views(environment),
					helpers=helpers,
					components=components,
				),
				helios.session.Provider(config.session(environment)),
				helios.database.provider.Provider(
					config.database(environment),
					registry(),
				),
				helios.form.Provider(),
				helios.auth.Provider(User),
			],
			[helios.limit.Middleware(config.rate_limit(environment))],
		)
		self.rescue(NotPermitted, Status.FORBIDDEN)
