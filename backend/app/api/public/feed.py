from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.database.session import get_session
from app.models import Post, User
from app.schemas.social import (
    CommentOut,
    CreateCommentRequest,
    CreatePostRequest,
    FeedResponse,
    LikeOut,
    PostOut,
)
from app.services import character_service, feed_service, social_service

feed_router = APIRouter(prefix="/feed", tags=["feed"])
posts_router = APIRouter(prefix="/posts", tags=["posts"])
comments_router = APIRouter(prefix="/comments", tags=["comments"])


@feed_router.get("", response_model=FeedResponse)
def get_feed(
    cursor: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    scope: str = Query(default="all"),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    viewer = character_service.get_active_character(session, user)
    return feed_service.list_feed(session, viewer, cursor, limit, scope=scope)


@posts_router.post("", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    req: CreatePostRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    author = character_service.require_active_character(session, user)
    post = feed_service.create_post(session, author, req)
    return feed_service.serialize_post(session, post, author)


@posts_router.get("/{post_id}", response_model=PostOut)
def get_post(
    post_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    post = session.get(Post, post_id)
    if post is None:
        from app.domain.errors import ServiceError

        raise ServiceError("Post não encontrado.", 404)
    author = character_service.get_active_character(session, user)
    return feed_service.serialize_post(session, post, author)


@posts_router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    actor = character_service.require_active_character(session, user)
    feed_service.delete_post(session, actor, post_id)


@posts_router.post("/{post_id}/like", response_model=LikeOut)
def like_post(
    post_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    actor = character_service.require_active_character(session, user)
    liked, count = social_service.toggle_post_like(session, actor, post_id)
    return LikeOut(liked=liked, likes_count=count)


@posts_router.delete("/{post_id}/like", response_model=LikeOut)
def unlike_post(
    post_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    actor = character_service.require_active_character(session, user)
    returned_liked = social_service.ensure_unliked(session, actor, "post", post_id)
    count = social_service.like_count(session, "post", post_id)
    return LikeOut(liked=returned_liked, likes_count=count)


@posts_router.get("/{post_id}/comments", response_model=list[CommentOut])
def list_comments(
    post_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    return social_service.comments_for(session, post_id)


@posts_router.post("/{post_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(
    post_id: int,
    req: CreateCommentRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    author = character_service.require_active_character(session, user)
    comment = social_service.add_comment(session, author, post_id, req.content, req.parent_comment_id)
    items = social_service.comments_for(session, post_id)
    return next(c for c in items if c.id == comment.id)


@comments_router.post("/{comment_id}/like", response_model=LikeOut)
def like_comment(
    comment_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    actor = character_service.require_active_character(session, user)
    liked, count = social_service.toggle_comment_like(session, actor, comment_id)
    return LikeOut(liked=liked, likes_count=count)


@comments_router.delete("/{comment_id}/like", response_model=LikeOut)
def unlike_comment(
    comment_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    actor = character_service.require_active_character(session, user)
    returned_liked = social_service.ensure_unliked(session, actor, "comment", comment_id)
    count = social_service.like_count(session, "comment", comment_id)
    return LikeOut(liked=returned_liked, likes_count=count)


@comments_router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    actor = character_service.require_active_character(session, user)
    social_service.delete_comment(session, actor, comment_id)