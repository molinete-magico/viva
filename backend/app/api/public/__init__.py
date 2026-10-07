from fastapi import APIRouter

from app.api.public import auth, characters, events, feed, messaging, notifications, relationships, world

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(world.router)
api_router.include_router(world.simulation_router)
api_router.include_router(feed.feed_router)
api_router.include_router(feed.posts_router)
api_router.include_router(feed.comments_router)
api_router.include_router(characters.router)
api_router.include_router(notifications.router)
api_router.include_router(messaging.router)
api_router.include_router(events.router)
api_router.include_router(relationships.router)
api_router.include_router(relationships.milestones_router)
