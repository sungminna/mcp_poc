import traceback
from urllib.parse import parse_qs
from django.contrib.auth.models import User, AnonymousUser
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

@database_sync_to_async
def get_user(user_id):
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()

class TokenAuthMiddleware:
    """
    Token authorization middleware for Django Channels.
    Reads a JWT from the query string.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        if token:
            try:
                access_token = AccessToken(token)
                user_id = access_token.get('user_id')
                if user_id:
                    scope['user'] = await get_user(user_id)
                else:
                    scope['user'] = AnonymousUser()
            except (InvalidToken, TokenError):
                # You might want to log this error
                print(f"Invalid token: {traceback.format_exc()}")
                scope['user'] = AnonymousUser()
            except Exception: # Catch any other unexpected errors during token processing
                print(f"Error processing token: {traceback.format_exc()}")
                scope['user'] = AnonymousUser()

        else:
            scope['user'] = AnonymousUser()
            
        # If no token is found, or if token is invalid,
        # proceed with AnonymousUser. The consumer can then decide to deny access.
        # Alternatively, you could raise an exception here to deny the connection immediately.

        return await self.app(scope, receive, send)

def TokenAuthMiddlewareStack(app):
    # This function is a simple wrapper if you prefer to call it this way in asgi.py
    # For consistency with AuthMiddlewareStack, but TokenAuthMiddleware itself is a valid ASGI app.
    return TokenAuthMiddleware(app) 