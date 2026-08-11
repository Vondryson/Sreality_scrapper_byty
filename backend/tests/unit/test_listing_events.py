from sreality_tracker.domain.events import (
    ListingEventType,
    ListingState,
    deactivation_event,
    observation_events,
)


def state(
    *, price: int | None = 1_000, detail_hash: str = "a", active: bool = True
) -> ListingState:
    return ListingState(price_czk=price, detail_hash=detail_hash, is_active=active)


def test_new_listing_only_emits_created() -> None:
    events = observation_events(None, state())

    assert [event.event_type for event in events] == [ListingEventType.CREATED]
    assert events[0].new_price_czk == 1_000


def test_observation_events_are_ordered_and_price_is_separate_from_detail() -> None:
    events = observation_events(
        state(price=2_000, detail_hash="old", active=False),
        state(price=1_000, detail_hash="new"),
    )

    assert [event.event_type for event in events] == [
        ListingEventType.REACTIVATED,
        ListingEventType.PRICE_DECREASED,
        ListingEventType.DETAILS_CHANGED,
    ]
    assert events[1].old_price_czk == 2_000
    assert events[1].new_price_czk == 1_000


def test_price_increase_does_not_imply_detail_change() -> None:
    events = observation_events(state(price=1_000), state(price=2_000))

    assert [event.event_type for event in events] == [ListingEventType.PRICE_INCREASED]


def test_unknown_price_transition_does_not_invent_direction() -> None:
    assert observation_events(state(price=None), state(price=1_000)) == ()
    assert observation_events(state(price=1_000), state(price=None)) == ()


def test_deactivation_is_only_emitted_once() -> None:
    event = deactivation_event(state(active=True))

    assert event is not None
    assert event.event_type is ListingEventType.DEACTIVATED
    assert deactivation_event(state(active=False)) is None
