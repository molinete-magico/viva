from sqlmodel import Session, select

from app.domain.errors import ServiceError
from app.llm import LLMError
from app.models import Character, Comment, Follow, Like, Location, Notification, Post
from app.schemas.social import CommentOut, comment_out
from app.services.character_service import photo_url_map
from app.services import relationship_service as rel


def _target_post(session: Session, post_id: int) -> Post:
    post = session.get(Post, post_id)
    if post is None:
        raise ServiceError("Post não encontrado.", 404)
    return post


def _target_comment(session: Session, comment_id: int) -> Comment:
    comment = session.get(Comment, comment_id)
    if comment is None:
        raise ServiceError("Comentário não encontrado.", 404)
    return comment


def _notify(
    session: Session,
    recipient_character_id: int,
    type_: str,
    payload: dict,
) -> None:
    session.add(Notification(character_id=recipient_character_id, type=type_, payload=payload))
    session.commit()


def _bump_discovery(session: Session, character: Character | None, min_level: int) -> None:
    if character is not None and character.is_npc and character.discovered_level < min_level:
        character.discovered_level = min_level
        session.add(character)
        session.commit()


def _like_count(session: Session, target_type: str, target_id: int) -> int:
    return len(session.exec(select(Like).where(Like.target_type == target_type, Like.target_id == target_id)).all())


def _ensure_liked(session: Session, actor: Character, target_type: str, target_id: int) -> bool:
    existing = session.exec(
        select(Like).where(
            Like.target_type == target_type,
            Like.target_id == target_id,
            Like.character_id == actor.id,
        )
    ).first()
    if existing is None:
        session.add(Like(target_type=target_type, target_id=target_id, character_id=actor.id))
        session.commit()
    return True


def toggle_post_like(session: Session, actor: Character, post_id: int) -> tuple[bool, int]:
    post = _target_post(session, post_id)
    liked = _ensure_liked(session, actor, "post", post_id)
    if liked and post.author_character_id != actor.id:
        _notify(
            session,
            post.author_character_id,
            "POST_LIKE",
            {"post_id": post.id, "actor_id": actor.id, "actor_name": actor.name},
        )
        author = session.get(Character, post.author_character_id)
        if author is not None:
            from app.services.social_arc_service import apply_engagement_consequences
            apply_engagement_consequences(
                session, actor=actor, author=author, post=post,
                moment=post.created_at, kind="like",
            )
        _bump_discovery(session, author, 2)
    return liked, _like_count(session, "post", post_id)


def toggle_comment_like(session: Session, actor: Character, comment_id: int) -> tuple[bool, int]:
    _target_comment(session, comment_id)
    liked = _ensure_liked(session, actor, "comment", comment_id)
    return liked, _like_count(session, "comment", comment_id)


def add_comment(
    session: Session,
    author: Character,
    post_id: int,
    content: str,
    parent_comment_id: int | None = None,
) -> Comment:
    content = content.strip()
    if not content:
        raise ServiceError("O comentário não pode ficar vazio.", 400)
    post = _target_post(session, post_id)
    if parent_comment_id is not None:
        _target_comment(session, parent_comment_id)
    comment = Comment(
        post_id=post_id,
        author_character_id=author.id,
        content=content,
        parent_comment_id=parent_comment_id,
    )
    session.add(comment)
    session.commit()
    session.refresh(comment)
    if post.author_character_id != author.id:
        _notify(
            session,
            post.author_character_id,
            "POST_COMMENT",
            {
                "post_id": post.id,
                "comment_id": comment.id,
                "actor_id": author.id,
                "actor_name": author.name,
            },
        )
        post_author = session.get(Character, post.author_character_id)
        if post_author is not None:
            comment_author = session.get(Character, comment.author_character_id)
            if comment_author is not None:
                from app.services.social_arc_service import apply_engagement_consequences
                apply_engagement_consequences(
                    session, actor=comment_author, author=post_author,
                    post=post, moment=comment.created_at, kind="comment",
                )
            _bump_discovery(session, post_author, 2)
    return comment


def comments_for(session: Session, post_id: int) -> list[CommentOut]:
    _target_post(session, post_id)
    comments = session.exec(
        select(Comment).where(Comment.post_id == post_id).order_by(Comment.id.asc())
    ).all()
    author_ids = {c.author_character_id for c in comments}
    if not author_ids:
        return []
    authors = {c.id: c for c in session.exec(select(Character).where(Character.id.in_(author_ids))).all()}
    photos = photo_url_map(session, list(authors.values()))
    return [
        comment_out(c, authors[c.author_character_id], photo_url=photos.get(c.author_character_id))
        for c in comments
    ]


def delete_comment(session: Session, actor: Character, comment_id: int) -> None:
    comment = _target_comment(session, comment_id)
    if comment.author_character_id != actor.id:
        raise ServiceError("Você só pode apagar seus próprios comentários.", 403)
    likes = session.exec(select(Like).where(Like.target_type == "comment", Like.target_id == comment_id)).all()
    for like in likes:
        session.delete(like)
    session.delete(comment)
    session.commit()


def follow_character(session: Session, follower: Character, target_id: int) -> tuple[bool, int]:
    target = session.get(Character, target_id)
    if target is None:
        raise ServiceError("Personagem não encontrado.", 404)
    if target.id == follower.id:
        raise ServiceError("Você não pode seguir a si mesmo.", 400)
    existing = session.exec(
        select(Follow).where(
            Follow.follower_character_id == follower.id,
            Follow.followed_character_id == target.id,
        )
    ).first()
    created = existing is None
    if created:
        session.add(Follow(follower_character_id=follower.id, followed_character_id=target.id))
        session.commit()
        rel.apply_changes(
            session, follower.id, target.id,
            {"familiarity": 1, "respect": 1},
            log=False,
        )
        _bump_discovery(session, target, 3)
        if not target.is_npc:
            _notify(
                session,
                target.id,
                "NEW_FOLLOWER",
                {"character_id": follower.id, "name": follower.name},
            )
        elif target.is_npc:
            _npc_follows_back(session, target, follower)
    return created, len(session.exec(select(Follow).where(Follow.followed_character_id == target.id)).all())


def _npc_follows_back(session: Session, npc: Character, human: Character) -> None:
    """Quando um humano segue um NPC, o morador devolve o follow (e avisa o humano)."""
    existing = session.exec(
        select(Follow).where(
            Follow.follower_character_id == npc.id,
            Follow.followed_character_id == human.id,
        )
    ).first()
    if existing is not None:
        return
    session.add(Follow(follower_character_id=npc.id, followed_character_id=human.id))
    session.commit()
    _notify(session, human.id, "NEW_FOLLOWER", {"character_id": npc.id, "name": npc.name})


def unfollow_character(session: Session, follower: Character, target_id: int) -> None:
    target = session.get(Character, target_id)
    if target is None:
        raise ServiceError("Personagem não encontrado.", 404)
    existing = session.exec(
        select(Follow).where(
            Follow.follower_character_id == follower.id,
            Follow.followed_character_id == target.id,
        )
    ).first()
    if existing is not None:
        session.delete(existing)
        session.commit()
        rel.apply_changes(
            session, follower.id, target.id,
            {"tension": 1},
            log=False,
        )
        rel.add_memory(
            session,
            owner_character_id=follower.id,
            other_character_id=target.id,
            content=f"Deixei de acompanhar {target.name}.",
            kind="social_graph_change",
            importance=16,
            dedupe_key=f"unfollow-{follower.id}-{target.id}-{__import__('datetime').datetime.now().date().isoformat()}",
        )


def ensure_unliked(session: Session, actor: Character, target_type: str, target_id: int) -> bool:
    existing = session.exec(
        select(Like).where(
            Like.target_type == target_type,
            Like.target_id == target_id,
            Like.character_id == actor.id,
        )
    ).first()
    if existing is not None:
        session.delete(existing)
        session.commit()
    return False


def like_count(session: Session, target_type: str, target_id: int) -> int:
    return _like_count(session, target_type, target_id)


def follower_count(session: Session, character_id: int) -> int:
    return len(session.exec(select(Follow).where(Follow.followed_character_id == character_id)).all())


def is_following(session: Session, follower_id: int, target_id: int) -> bool:
    return (
        session.exec(
            select(Follow).where(
                Follow.follower_character_id == follower_id,
                Follow.followed_character_id == target_id,
            )
        ).first()
        is not None
    )


def npc_autonomous_social_pulse(session: Session) -> tuple[int, int]:
    """Simula encontros NPC↔NPC sem depender do jogador.

    O relógio/rotina determina onde os NPCs estão; este pulso só transforma
    co-presença em uma interação ocasional. O relacionamento funciona como
    cooldown persistente: o mesmo par não recebe outro pulso em poucos minutos.
    Cada encontro deixa uma memória para os dois lados.
    """
    from datetime import datetime, timedelta, timezone

    npcs = session.exec(
        select(Character).where(
            Character.is_npc.is_(True),
            Character.current_location_id.is_not(None),
        )
    ).all()
    by_location: dict[int, list[Character]] = {}
    for npc in npcs:
        if npc.current_location_id is not None:
            by_location.setdefault(npc.current_location_id, []).append(npc)

    interactions = 0
    memories = 0
    now = datetime.now(timezone.utc)

    for occupants in by_location.values():
        if len(occupants) < 2:
            continue
        occupants = sorted(occupants, key=lambda character: character.id or 0)
        for left, right in zip(occupants, occupants[1:]):
            if left.id is None or right.id is None:
                continue
            relationship = rel.relationship_between(session, left.id, right.id)
            if relationship is not None and relationship.last_interaction_at:
                if relationship.last_interaction_at > now - timedelta(minutes=90):
                    continue

            rel.bump_interaction(
                session,
                left.id,
                right.id,
                {"familiarity": 1, "friendship": 1, "respect": 1},
            )
            interactions += 1

            location_name = session.get(Location, left.current_location_id)
            place = location_name.name if location_name else "um lugar da cidade"
            for owner, other in ((left, right), (right, left)):
                memory = rel.add_memory(
                    session,
                    owner_character_id=owner.id,
                    other_character_id=other.id,
                    content=f"Encontrei {other.name} em {place}; trocamos algumas palavras.",
                    category="NORMAL",
                    kind="npc_encounter",
                    importance=25,
                    context={"location_id": owner.current_location_id},
                    dedupe_key=f"npc-encounter-{owner.id}-{other.id}-{now.date().isoformat()}",
                )
                if memory.id:
                    memories += 1

    return interactions, memories


def npc_social_reactions(session: Session) -> tuple[int, int]:
    """NPCs que seguem um humano(a) reagem aos posts dele(a).

    Roda a cada avanço de simulação acionado pelo usuário (idempotente): cada NPC
    seguidor que ainda não curtiu curte o post (no máximo 3 por post) e um NPC
    comenta o post — apenas se ainda não houver comentário de NPC ali. Retorna
    (curtidas_aplicadas, comentarios_criados).
    """
    from collections import defaultdict

    rows = session.exec(
        select(Post, Character)
        .join(Character, Post.author_character_id == Character.id)
        .where(Character.is_npc.is_(False))
    ).all()
    if not rows:
        return 0, 0

    author_ids = {post.author_character_id for post, _ in rows}
    follows = session.exec(
        select(Follow).where(Follow.followed_character_id.in_(author_ids))
    ).all()
    by_author: dict[int, list[Character]] = defaultdict(list)
    if follows:
        follower_ids = {f.follower_character_id for f in follows}
        characters = {
            c.id: c
            for c in session.exec(select(Character).where(Character.id.in_(follower_ids))).all()
        }
        for follow in follows:
            actor = characters.get(follow.follower_character_id)
            if actor is not None and actor.is_npc:
                by_author[follow.followed_character_id].append(actor)

    import random

    likes_applied = 0
    comments_applied = 0
    for post, _ in rows:
        npc_followers = by_author.get(post.author_character_id) or []
        if not npc_followers:
            continue

        for actor in random.sample(npc_followers, min(3, len(npc_followers))):
            existing = session.exec(
                select(Like).where(
                    Like.target_type == "post",
                    Like.target_id == post.id,
                    Like.character_id == actor.id,
                )
            ).first()
            if existing is not None:
                continue
            session.add(Like(target_type="post", target_id=post.id, character_id=actor.id))
            session.commit()
            _notify(
                session,
                post.author_character_id,
                "POST_LIKE",
                {"post_id": post.id, "actor_id": actor.id, "actor_name": actor.name},
            )
            likes_applied += 1

        npc_comment = session.exec(
            select(Comment)
            .join(Character, Comment.author_character_id == Character.id)
            .where(Comment.post_id == post.id, Character.is_npc.is_(True))
            .limit(1)
        ).first()
        if npc_comment is not None:
            continue

        actor = npc_followers[0]
        from app.services.llm_service import generate_npc_comment

        try:
            text = generate_npc_comment(session, actor, post)
        except LLMError:
            text = ""
        if not text.strip():
            continue
        comment = Comment(post_id=post.id, author_character_id=actor.id, content=text.strip())
        session.add(comment)
        session.commit()
        session.refresh(comment)
        _notify(
            session,
            post.author_character_id,
            "POST_COMMENT",
            {
                "post_id": post.id,
                "comment_id": comment.id,
                "actor_id": actor.id,
                "actor_name": actor.name,
            },
        )
        comments_applied += 1

    return likes_applied, comments_applied