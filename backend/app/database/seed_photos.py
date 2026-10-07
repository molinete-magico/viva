import logging
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from sqlmodel import Session, select

from app.config import DATA_DIR
from app.database.seed_world import NPCS
from app.models import Character, CharacterPhoto

logger = logging.getLogger("viva.seed")

PHOTOS_DIR = DATA_DIR / "photos"


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value.lower())
    ascii_value = "".join(c for c in normalized if not unicodedata.combining(c))
    return "".join(c if c.isalnum() else "-" for c in ascii_value).strip("-")


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _darker(rgb: tuple[int, int, int], factor: float = 0.75) -> tuple[int, int, int]:
    return tuple(int(c * factor) for c in rgb)  # type: ignore[return-value]


def generate_avatar(name: str, color_hex: str, size: int = 512) -> Path:
    PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    path = PHOTOS_DIR / f"npc-{slugify(name)}.png"
    if path.exists():
        return path

    bg = hex_to_rgb(color_hex)
    img = Image.new("RGB", (size, size), bg)
    draw = ImageDraw.Draw(img)

    margin = size // 7
    draw.ellipse([margin, margin, size - margin, size - margin], outline=_darker(bg), width=size // 48)

    initial = name.strip()[:1].upper()
    font = ImageFont.load_default(size=int(size * 0.42))
    bbox = draw.textbbox((0, 0), initial, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(
        ((size - text_w) / 2 - bbox[0], (size - text_h) / 2 - bbox[1] - size * 0.02),
        initial,
        font=font,
        fill=(255, 252, 247),
    )

    img.save(path, "PNG")
    logger.info("generated avatar %s", path.name)
    return path


def ensure_npc_photos(session: Session) -> None:
    for data in NPCS:
        character = session.exec(
            select(Character).where(Character.name == data["name"], Character.is_npc == True)  # noqa: E712
        ).first()
        if character is None or character.photo_id is not None:
            continue
        file_path = generate_avatar(data["name"], data["photo_color"])
        photo = CharacterPhoto(
            character_id=character.id,
            source="seed",
            path=f"/static/photos/{file_path.name}",
            label="foto inicial",
            is_primary=True,
        )
        session.add(photo)
        session.commit()
        session.refresh(photo)
        character.photo_id = photo.id
        session.add(character)
        session.commit()
