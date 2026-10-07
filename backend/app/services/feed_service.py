from sqlalchemy import func
from sqlmodel import Session, select

from app.domain.errors import ServiceError
from app.models import Character, Like, Post
from app.schemas.social import CreatePostRequest, FeedResponse, PostOut, post_out


def serialize_posts(session: Session, posts: list[Post], viewer: Character | None) -> FeedResponse:
    if not posts:
        return FeedResponse(items=[], next_cursor=None)
    post_ids = [p.id for p in posts]
    author_ids = {p.author_character_id for p in posts}
    authors = {c.id: c for c in session.exec(select(Character).where(Character.id.in_(author_ids))).all()}
    like_rows = session.exec(
        select(Like.target_id, func.count(Like.id))
        .where(Like.target_type == "post", Like.target_id.in_(post_ids))
        .group_by(Like.target_id)
    ).all()
    like_counts = {row[0]: row[1] for row in like_rows}
    from app.models import Comment

    comment_rows = session.exec(
        select(Comment.post_id, func.count(Comment.id))
        .where(Comment.post_id.in_(post_ids))
        .group_by(Comment.post_id)
    ).all()
    comment_counts = {row[0]: row[1] for row in comment_rows}
    from app.services.character_service import photo_url_map

    photos = photo_url_map(session, list(authors.values()))
    liked_ids: set[int] = set()
    if viewer is not None:
        liked_rows = session.exec(
            select(Like.target_id)
            .where(
                Like.target_type == "post",
                Like.character_id == viewer.id,
                Like.target_id.in_(post_ids),
            )
        ).all()
        liked_ids = set(liked_rows)

    items: list[PostOut] = []
    for post in posts:
        author = authors.get(post.author_character_id)
        if author is None:
            continue
        items.append(
            post_out(
                post,
                author,
                likes=like_counts.get(post.id, 0),
                comments=comment_counts.get(post.id, 0),
                liked=post.id in liked_ids,
                photo_url=photos.get(author.id),
            )
        )
    return FeedResponse(items=items, next_cursor=None)


def list_feed(
    session: Session,
    viewer: Character | None,
    cursor: int | None,
    limit: int,
    scope: str = "all",
) -> FeedResponse:
    from sqlalchemy import or_

    from app.models import Follow

    query = select(Post).order_by(Post.id.desc())
    followed: list[int] = []
    if viewer is not None:
        followed = session.exec(
            select(Follow.followed_character_id).where(Follow.follower_character_id == viewer.id)
        ).all()
    if viewer is not None and scope == "following":
        query = query.where(or_(Post.author_character_id == viewer.id, Post.author_character_id.in_(list(followed))))
    if cursor is not None:
        query = query.where(Post.id < cursor)

    if viewer is not None and scope in ("for_you", "popular"):
        # Descoberta usa uma janela curta para não quebrar paginação histórica.
        candidates = session.exec(query.limit(100).all()).all()
        from datetime import datetime, timezone
        from app.models import Comment, Relationship
        now = datetime.now(timezone.utc)
        def relevance(post: Post) -> float:
            age_hours = max(0.25, (now - post.created_at).total_seconds() / 3600)
            likes = len(session.exec(select(Like.id).where(Like.target_type == "post", Like.target_id == post.id)).all())
            comments = len(session.exec(select(Comment.id).where(Comment.post_id == post.id)).all())
            score = likes * 2.0 + comments * 3.0
            if post.author_character_id in followed:
                score += 5.0
            relationship = session.exec(
                select(Relationship).where(
                    ((Relationship.character_a_id == viewer.id) & (Relationship.character_b_id == post.author_character_id))
                    | ((Relationship.character_a_id == post.author_character_id) & (Relationship.character_b_id == viewer.id))
                )
            ).first()
            if relationship:
                score += relationship.friendship * 0.08 + relationship.familiarity * 0.03 - relationship.tension * 0.05
            score += 8.0 / age_hours
            return score
        posts = sorted(candidates, key=relevance, reverse=True)[:limit + 1]
    else:
        posts = session.exec(query.limit(limit + 1)).all()
    next_cursor = None
    if len(posts) > limit:
        posts = posts[:limit]
        next_cursor = posts[-1].id
    result = serialize_posts(session, posts, viewer)
    result.next_cursor = next_cursor
    return result


def delete_post(session: Session, actor: Character, post_id: int) -> None:
    from app.models import Comment, Like

    post = session.get(Post, post_id)
    if post is None:
        raise ServiceError("Post não encontrado.", 404)
    if post.author_character_id != actor.id:
        raise ServiceError("Você só pode apagar seus próprios posts.", 403)
    comment_ids = [c.id for c in session.exec(select(Comment.id).where(Comment.post_id == post.id)).all()]
    for like in session.exec(select(Like).where(Like.target_type == "post", Like.target_id == post.id)).all():
        session.delete(like)
    for comment in session.exec(select(Comment).where(Comment.post_id == post.id)).all():
        session.delete(comment)
    session.delete(post)
    session.commit()


def create_post(session: Session, author: Character, req: CreatePostRequest) -> Post:
    content = req.content.strip()
    if not content:
        raise ServiceError("O post não pode ficar vazio.", 400)
    if req.location_id is not None:
        from app.models import Location

        if session.get(Location, req.location_id) is None:
            raise ServiceError("Local não encontrado.", 404)
    post = Post(author_character_id=author.id, content=content, location_id=req.location_id)
    session.add(post)
    session.commit()
    session.refresh(post)
    return post


def serialize_post(session: Session, post: Post, viewer: Character | None) -> PostOut:
    return serialize_posts(session, [post], viewer).items[0]
