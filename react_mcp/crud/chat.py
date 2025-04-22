from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from models.chat import ChatSession, ChatMessage
from typing import List


async def create_session(db: AsyncSession, user_id: int) -> ChatSession:
    session = ChatSession(user_id=user_id)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session(db: AsyncSession, session_id: int) -> ChatSession:
    result = await db.execute(select(ChatSession).filter(ChatSession.id == session_id))
    return result.scalars().first()


async def create_chat_message(db: AsyncSession, session_id: int, sender: str, content: str) -> ChatMessage:
    message = ChatMessage(session_id=session_id, sender=sender, content=content)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_messages(db: AsyncSession, session_id: int) -> List[ChatMessage]:
    result = await db.execute(
        select(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return result.scalars().all()


async def get_sessions(db: AsyncSession, user_id: int) -> List[ChatSession]:
    result = await db.execute(
        select(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.created_at.desc())
    )
    return result.scalars().all()


async def delete_session(db: AsyncSession, session_id: int) -> None:
    # Delete all messages linked to this session asynchronously
    await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    
    # Delete the session itself asynchronously
    # We need to get the session first to delete it by object, or use delete by filter
    # Option 1: Get then delete (might be less efficient)
    # session = await get_session(db, session_id)
    # if session:
    #     await db.delete(session)
    
    # Option 2: Delete directly using a filter (more efficient)
    await db.execute(delete(ChatSession).where(ChatSession.id == session_id))

    await db.commit() 