from amqtt.plugins.authentication import BaseAuthPlugin
from app.middleware.auth.requireAuth import get_user_from_bearer


class OAuthPlugin(BaseAuthPlugin):
    def __init__(self, context):
        super().__init__(context)

    async def authenticate(self, *args, **kwargs):
        authenticated = super().authenticate(*args, **kwargs)

        if not authenticated:
            return authenticated

        session = kwargs.get('session', None)

        # we do not care about username as all info is contained in jwt
        if (session is None or session.password is None):
            return False

        jwt = session.password

        print('tyring to use jwt toen for authentication')

        try:
            user = get_user_from_bearer(jwt)

            print('auth')

            return True
        except Exception:
            return False
        