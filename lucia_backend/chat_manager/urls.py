from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatRoomViewSet, MessageListView

router = DefaultRouter()
router.register(r'rooms', ChatRoomViewSet, basename='room')

urlpatterns = [
    path('', include(router.urls)),
    path('rooms/<int:room_pk>/messages/', MessageListView.as_view(), name='message-list'),
]
