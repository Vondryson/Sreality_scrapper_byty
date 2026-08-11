"""Pure listing lifecycle transitions independent of persistence."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ListingEventType(StrEnum):
    CREATED = "created"
    PRICE_DECREASED = "price_decreased"
    PRICE_INCREASED = "price_increased"
    DETAILS_CHANGED = "details_changed"
    DEACTIVATED = "deactivated"
    REACTIVATED = "reactivated"


@dataclass(frozen=True, slots=True)
class ListingState:
    price_czk: int | None
    detail_hash: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class EventDraft:
    event_type: ListingEventType
    old_price_czk: int | None = None
    new_price_czk: int | None = None
    changes: dict[str, object] | None = None


def observation_events(
    previous: ListingState | None, current: ListingState
) -> tuple[EventDraft, ...]:
    """Return ordered events caused by observing the current listing state."""
    if not current.is_active:
        raise ValueError("an observed listing state must be active")
    if previous is None:
        return (
            EventDraft(
                ListingEventType.CREATED,
                new_price_czk=current.price_czk,
                changes={"is_active": {"old": None, "new": True}},
            ),
        )

    events: list[EventDraft] = []
    if not previous.is_active:
        events.append(
            EventDraft(
                ListingEventType.REACTIVATED,
                old_price_czk=previous.price_czk,
                new_price_czk=current.price_czk,
                changes={"is_active": {"old": False, "new": True}},
            )
        )
    if previous.price_czk is not None and current.price_czk is not None:
        if current.price_czk < previous.price_czk:
            events.append(
                EventDraft(
                    ListingEventType.PRICE_DECREASED,
                    old_price_czk=previous.price_czk,
                    new_price_czk=current.price_czk,
                )
            )
        elif current.price_czk > previous.price_czk:
            events.append(
                EventDraft(
                    ListingEventType.PRICE_INCREASED,
                    old_price_czk=previous.price_czk,
                    new_price_czk=current.price_czk,
                )
            )
    if previous.detail_hash != current.detail_hash:
        events.append(
            EventDraft(
                ListingEventType.DETAILS_CHANGED,
                old_price_czk=previous.price_czk,
                new_price_czk=current.price_czk,
                changes={
                    "detail_hash": {
                        "old": previous.detail_hash,
                        "new": current.detail_hash,
                    }
                },
            )
        )
    return tuple(events)


def deactivation_event(previous: ListingState) -> EventDraft | None:
    """Return a deactivation draft only for an active listing."""
    if not previous.is_active:
        return None
    return EventDraft(
        ListingEventType.DEACTIVATED,
        old_price_czk=previous.price_czk,
        new_price_czk=previous.price_czk,
        changes={"is_active": {"old": True, "new": False}},
    )
