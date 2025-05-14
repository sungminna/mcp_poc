import json
from channels.generic.websocket import AsyncWebsocketConsumer

from openai.types.responses import ResponseTextDeltaEvent
from .agent import agent


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        # Handle incoming user message and stream assistant tokens
        if not text_data:
            return
        payload = json.loads(text_data)
        content = payload.get('message')
        # Broadcast the user message to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {'type': 'chat_message', 'message': {'role': 'user', 'content': content}}
        )
        # Stream assistant response tokens
        config = {'configurable': {'thread_id': self.room_name}}
        # stream_mode='messages' streams tokens
        async for token, meta in agent.astream(
            {'messages': [{'role': 'user', 'content': content}]},
            config,
            stream_mode='messages'
        ):
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'chat_message', 'message': {'role': 'assistant', 'token': token}}
            )

    async def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        })) 