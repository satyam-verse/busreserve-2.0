"""City directory database model for dynamic Indian city search and alias resolution."""

from datetime import UTC, datetime

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(UTC)


class City(db.Model):
    """Searchable Indian city entry with optional state and alternate spelling aliases."""

    __tablename__ = "cities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    state = db.Column(db.String(100), nullable=True)
    aliases = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    def alias_list(self) -> list[str]:
        if not self.aliases:
            return []
        return [token.strip() for token in self.aliases.split(",") if token.strip()]

    def to_dict(self, has_routes: bool | None = None) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "aliases": self.alias_list(),
            "latitude": self.latitude,
            "longitude": self.longitude,
            "is_active": self.is_active,
        }
        if has_routes is not None:
            data["has_routes"] = has_routes
        return data
