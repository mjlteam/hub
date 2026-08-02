"""Authentication module and its OAuth client configuration."""

from authlib.integrations.flask_client import OAuth


oauth = OAuth()


def init_oauth(app):
    """Bind Authlib to the Flask app and register the GitHub provider."""
    oauth.init_app(app)
    oauth.register(
        name='github',
        client_id=app.config.get('GITHUB_CLIENT_ID'),
        client_secret=app.config.get('GITHUB_CLIENT_SECRET'),
        access_token_url='https://github.com/login/oauth/access_token',
        authorize_url='https://github.com/login/oauth/authorize',
        api_base_url='https://api.github.com/',
        client_kwargs={'scope': 'read:user user:email'},
    )


__all__ = ['oauth', 'init_oauth']
