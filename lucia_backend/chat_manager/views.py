from django.shortcuts import render
from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import ChatRoom
from .serializers import ChatRoomSerializer
from .agent import agent

# Create your views here.

class ChatRoomViewSet(viewsets.ModelViewSet):
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ChatRoom.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ChatHistoryView(APIView):
    """Return past chat history for a given thread via PostgresSaver state."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, room_pk):
        # room_pk used as thread_id
        room = get_object_or_404(ChatRoom, pk=room_pk, user=request.user)
        thread_id = str(room.pk)
        config = {"configurable": {"thread_id": thread_id}}
        state_snapshot = agent.get_state(config)
        # Get message history from agent state
        messages = state_snapshot.values.get("messages", [])
        # Serialize for front-end
        data = [{"role": msg.role, "content": msg.content} for msg in messages]
        return Response(data)
