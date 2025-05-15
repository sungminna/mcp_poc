import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import logging
from langchain_openai.chat_models.base import OpenAIRefusalError
from langchain_core.runnables import RunnableConfig

from .models import ChatRoom, Message
from .agent import agent

logger = logging.getLogger(__name__)

@database_sync_to_async
def save_message(room, user, content):
    """Save a message to the database"""
    return Message.objects.create(room=room, user=user, content=content)

@database_sync_to_async
def get_chat_room(room_id, user):
    """Fetch the ChatRoom instance for the given room_id and user"""
    return ChatRoom.objects.get(pk=room_id, user=user)

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get("user")
        # Ensure authenticated user
        if not self.user or self.user.is_anonymous or not self.user.is_authenticated:
            logger.warning(
                f"Unauthenticated WebSocket connection attempt closed. User: {self.user}, Scope: {self.scope.get('query_string', b'').decode()}"
            )
            await self.close()
            return
        logger.info(f"Authenticated user {self.user} (ID: {self.user.pk}) attempting to connect via WebSocket.")

        # Get room_id from URL kwargs (now an integer due to routing change)
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        logger.debug(f"Room ID: {self.room_id}")
        try:
            # Fetch the chat room by its primary key and ensure the user owns it
            self.room = await get_chat_room(self.room_id, self.user)
            logger.info(f"User {self.user} (ID: {self.user.pk}) successfully found room {self.room_id}.")
        except ChatRoom.DoesNotExist:
            logger.warning(f"ChatRoom with pk={self.room_id} not found for user {self.user} (ID: {self.user.pk}). Closing connection.")
            await self.close()
            return
        except Exception as e: # Catch other potential errors during DB lookup
            logger.error(f"Error fetching chat room pk={self.room_id} for user {self.user} (ID: {self.user.pk}): {e}")
            await self.close()
            return

        self.room_group_name = f'chat_{self.room.pk}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"WebSocket connection accepted for user {self.user} (ID: {self.user.pk}) to room {self.room.pk} (group: {self.room_group_name})")

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        logger.info(f"WebSocket connection closed for user {getattr(self, 'user', 'Unknown')} with code {close_code}")

    # Add broadcast_message and send_json_message helper methods
    async def broadcast_message(self, message):
        # Broadcast a message to the room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    async def send_json_message(self, message):
        # Send a JSON message directly to the WebSocket client
        await self.send(text_data=json.dumps({'message': message}))

    async def receive(self, text_data=None, bytes_data=None):
        # Handle incoming user message and stream assistant events
        if not text_data:
            return
        
        try:
            payload = json.loads(text_data)
            content = payload.get('message')
            
            if not content:
                logger.warning(f"Received empty message from user {self.user.pk} in room {self.room.pk}")
                return
            
            # Save user message to database
            await save_message(self.room, self.user, content)
            user_message = {'role': 'user', 'type': 'message', 'content': content}
            await self.broadcast_message(user_message)
                
            # Create RunnableConfig for streaming (required for Python <3.11 async)
            config = RunnableConfig(configurable={
                'thread_id': str(self.room.pk),
                'user_name': getattr(self.user, 'username', 'User')
            })
            
            assistant_response = ""
            
            # Force stream_mode for agent interaction to stream LLM token messages
            agent_interaction_stream_mode = "messages"

            try:
                async for chunk, metadata in agent.astream(
                    {'messages': [{'role': 'user', 'content': content}]},
                    config,
                    stream_mode=agent_interaction_stream_mode
                ):
                    # Only process assistant token chunks
                    
                    if chunk.content:
                        token_content = chunk.content
                        # Include metadata for graph node and LLM invocation details
                        out_message = {
                            'role': 'assistant',
                            'type': 'token',
                            'token': token_content,
                            'metadata': metadata
                        }
                        # Direct send token to client to avoid group capacity limits
                        await self.send_json_message(out_message)
                        assistant_response += token_content

            except OpenAIRefusalError as e:
                logger.warning("OpenAI refusal error", exc_info=e)
                error_message = {
                    'role': 'system',
                    'type': 'error',
                    'content': f"AI 모델이 요청 처리를 거부했습니다. 세부 정보: {str(e)}"
                }
                await self.send_json_message(error_message)
            except Exception:
                logger.exception("Error streaming response")
                await self.send_json_message({'role': 'system', 'type': 'error', 'content': '응답 생성 중 오류가 발생했습니다.'})
            finally:
                # After streaming completes (loop finishes or error), notify client that the stream is done
                done_message = {'role': 'assistant', 'type': 'done'}
                # Direct send done message to bypass group capacity
                await self.send_json_message(done_message)
                
                # Then save the full assistant response
                if assistant_response:
                    await save_message(self.room, self.user, assistant_response)
                    
        except json.JSONDecodeError:
            logger.exception(f"Invalid JSON received from user {self.user.pk}")
        except Exception:
            logger.exception("Error in receive")

    async def chat_message(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

    # Add send_json compatibility for any calls to send_json
    async def send_json(self, content, close=False, **kwargs):
        # Send JSON content over WebSocket
        await self.send(text_data=json.dumps(content), close=close, **kwargs)