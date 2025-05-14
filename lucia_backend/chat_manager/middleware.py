import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.auth import AuthMiddlewareStack
from rest_framework_simplejwt.tokens import UntypedToken
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model

@database_sync_to_async
def get_user(validated_token):
    User = get_user_model()
    user_id = validated_token.get('user_id')
    return User.objects.get(id=user_id)

class JWTAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        return JWTAuthMiddlewareInstance(scope, self.inner)

class JWTAuthMiddlewareInstance:
    def __init__(self, scope, inner):
        self.scope = dict(scope)
        self.inner = inner

    async def __call__(self, receive, send):
        # Extract token from query string
        query_string = self.scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token_list = params.get('token', None)
        if token_list:
            token = token_list[0]
            try:
                validated_token = UntypedToken(token)
                self.scope['user'] = await get_user(validated_token.payload)
            except Exception:
                self.scope['user'] = AnonymousUser()
        else:
            self.scope['user'] = AnonymousUser()

        inner = self.inner(self.scope)
        return await inner(receive, send)

def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(AuthMiddlewareStack(inner)) 