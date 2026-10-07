from datetime import datetime

from pydantic import BaseModel, Field

from app.models import Character, Comment, Post
from app.schemas.auth import CharacterOut, character_out


class AuthorBrief(BaseModel):
    id: int
    name: str
    profession_label: str
    photo_url: str | None = None


class CreatePostRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    location_id: int | None = None


class PostOut(BaseModel):
    id: int
    content: str
    kind: str
    created_at: datetime
    author: AuthorBrief
    likes_count: int = 0
    comments_count: int = 0
    liked_by_me: bool = False


class FeedResponse(BaseModel):
    items: list[PostOut]
    next_cursor: int | None = None


class CommentOut(BaseModel):
    id: int
    post_id: int
    content: str
    created_at: datetime
    author: AuthorBrief


class CreateCommentRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    parent_comment_id: int | None = None


class LikeOut(BaseModel):
    liked: bool
    likes_count: int


class FollowOut(BaseModel):
    following: bool
    followers_count: int


def author_brief(character: Character, photo_url: str | None = None) -> AuthorBrief:
    return AuthorBrief(
        id=character.id,
        name=character.name,
        profession_label=character.profession_label,
        photo_url=photo_url,
    )


def post_out(
    post: Post,
    author: Character,
    likes: int = 0,
    comments: int = 0,
    liked: bool = False,
    photo_url: str | None = None,
) -> PostOut:
    return PostOut(
        id=post.id,
        content=post.content,
        kind=post.kind,
        created_at=post.created_at,
        author=author_brief(author, photo_url=photo_url),
        likes_count=likes,
        comments_count=comments,
        liked_by_me=liked,
    )


def comment_out(comment: Comment, author: Character, photo_url: str | None = None) -> CommentOut:
    return CommentOut(
        id=comment.id,
        post_id=comment.post_id,
        content=comment.content,
        created_at=comment.created_at,
        author=author_brief(author, photo_url=photo_url),
    )


__all__ = [
    "AuthorBrief",
    "CommentOut",
    "CreateCommentRequest",
    "CreatePostRequest",
    "FeedResponse",
    "FollowOut",
    "LikeOut",
    "PostOut",
    "author_brief",
    "comment_out",
    "post_out",
    "CharacterOut",
    "character_out",
]
