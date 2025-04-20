from sqlalchemy.orm import Session
from models.chat import ChatSession, ChatMessage
from typing import List


def create_session(db: Session, user_id: int) -> ChatSession:
    session = ChatSession(user_id=user_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: int) -> ChatSession:
    return db.query(ChatSession).filter(ChatSession.id == session_id).first()


def create_chat_message(db: Session, session_id: int, sender: str, content: str) -> ChatMessage:
    message = ChatMessage(session_id=session_id, sender=sender, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_messages(db: Session, session_id: int) -> List[ChatMessage]:
    return db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()


def get_sessions(db: Session, user_id: int) -> List[ChatSession]:
    return db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc()).all()


def delete_session(db: Session, session_id: int) -> None:
    # Delete all messages linked to this session
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    # Delete the session itself
    session = get_session(db, session_id)
    if session:
        db.delete(session)
        db.commit() 