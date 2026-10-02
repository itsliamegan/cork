from app.config import Config, ENV_FILE
from app.wsgi import Application

app = Application(Config.load(env_file=ENV_FILE))
