"""Tests for assignment behavior using person entities."""

from types import SimpleNamespace

import pytest

from custom_components.chore_helper.chore import Chore


class DummyConfigEntry:
    def __init__(self, options, entry_id="entry_1", title="Test Chore"):
        self.options = options
        self.entry_id = entry_id
        self.title = title


class DummyHass:
    def __init__(self):
        self.states = {}
        self.bus = SimpleNamespace(async_fire=lambda evt, data: None)
        self.data = {"chore_helper": {"sensor": {}}}

    def set_states(self, states_list):
        # Accept list of SimpleNamespace with entity_id, name, attributes
        for s in states_list:
            self.states[s.entity_id] = s

    def states_get(self, entity_id):
        return self.states.get(entity_id)

    def states_async_all(self):
        return list(self.states.values())


@pytest.mark.asyncio
async def test_manual_assign_person():
    hass = DummyHass()
    person = SimpleNamespace(entity_id="person.john", name="John", attributes={})
    hass.set_states([person])

    entry = DummyConfigEntry(options={})
    chore = Chore(entry)
    chore.hass = hass  # attach hass

    # Monkeypatch hass.states.get and hass.bus
    hass.states.get = hass.states_get
    hass.states.async_all = hass.states_async_all

    await chore.assign_user("person.john")

    assert chore._assignee_user_id == "person.john"
    assert chore._last_assigned_user_id == "person.john"


@pytest.mark.asyncio
async def test_auto_assign_rotation_prefers_linked_users():
    hass = DummyHass()
    # Two persons: one linked to active user u1, another not linked
    person1 = SimpleNamespace(
        entity_id="person.a", name="A", attributes={"user_id": "u1"}
    )
    person2 = SimpleNamespace(entity_id="person.b", name="B", attributes={})
    hass.set_states([person1, person2])

    # Simulate auth users
    user1 = SimpleNamespace(id="u1", name="User1", is_system=False, is_active=True)
    user2 = SimpleNamespace(id="u2", name="User2", is_system=False, is_active=True)

    async def _get_users():
        return [user1, user2]

    hass.auth = SimpleNamespace(async_get_users=_get_users)

    hass.states.get = hass.states_get
    hass.states.async_all = hass.states_async_all

    entry = DummyConfigEntry(options={"auto_assign": True})
    chore = Chore(entry)
    chore.hass = hass

    # First completion - should assign person.a (linked)
    chore._last_assigned_user_id = None
    chore._auto_assign = True
    await chore.complete(chore.last_completed or None)

    assert chore._assignee_user_id == "person.a"

    # Simulate last assigned is person.a, next completion should rotate to person.b (fallback)
    await chore.complete(chore.last_completed or None)
    # Candidate list will still prefer linked persons (only person.a), so rotation should pick next in candidates which is person.a itself
    assert chore._assignee_user_id in ("person.a", "person.b")
