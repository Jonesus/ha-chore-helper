"""Tests for config flow assignee selector fallback behavior."""

from types import SimpleNamespace

import pytest


from custom_components.chore_helper import config_flow


@pytest.mark.asyncio
async def test_assignee_dropdown_fallback_in_config() -> None:
    """Ensure a dropdown is built from person entities for assignee selection."""

    person1 = SimpleNamespace(entity_id="person.p1", name="Alice")
    person2 = SimpleNamespace(entity_id="person.p2", name="Bob")

    async def _get_states():
        return [person1, person2]

    fake_hass = SimpleNamespace(states=SimpleNamespace(async_all=_get_states))
    handler = SimpleNamespace(options={}, hass=fake_hass)

    schema = await config_flow.general_config_schema(handler, hass=fake_hass)

    # Search schema for a SelectSelector whose options include our test persons
    def opt_value(o):
        if isinstance(o, dict):
            return o.get("value")
        return getattr(o, "value", None)

    found = False
    schema_mapping = getattr(schema, "schema", None) or {}
    for val in schema_mapping.values():
        if isinstance(val, config_flow.selector.SelectSelector):
            cfg = getattr(val, "config", {})
            opts = (
                cfg.get("options")
                if isinstance(cfg, dict)
                else getattr(cfg, "options", [])
            )
            if any(opt_value(o) == "person.p1" for o in (opts or [])):
                found = True
                break

    assert (
        found
    ), "Assignee SelectSelector with person options not found in config schema"


@pytest.mark.asyncio
async def test_assignee_dropdown_fallback_in_options() -> None:
    """Ensure the options flow provides a dropdown built from person entities."""

    person1 = SimpleNamespace(entity_id="person.p1", name="Alice")
    person2 = SimpleNamespace(entity_id="person.p2", name="Bob")

    async def _get_states():
        return [person1, person2]

    fake_hass = SimpleNamespace(states=SimpleNamespace(async_all=_get_states))
    handler = SimpleNamespace(options={}, hass=fake_hass)

    schema = await config_flow.general_options_schema(handler, hass=fake_hass)

    def opt_value(o):
        if isinstance(o, dict):
            return o.get("value")
        return getattr(o, "value", None)

    found = False
    schema_mapping = getattr(schema, "schema", None) or {}
    for val in schema_mapping.values():
        if isinstance(val, config_flow.selector.SelectSelector):
            cfg = getattr(val, "config", {})
            opts = (
                cfg.get("options")
                if isinstance(cfg, dict)
                else getattr(cfg, "options", [])
            )
            if any(opt_value(o) == "person.p1" for o in (opts or [])):
                found = True
                break

    assert (
        found
    ), "Assignee SelectSelector with person options not found in options schema"


@pytest.mark.asyncio
async def test_assignee_select_when_person_fetch_fails() -> None:
    """If fetching persons fails, still provide a SelectSelector with a placeholder option."""

    async def _get_states():
        raise Exception("nope")

    fake_hass = SimpleNamespace(states=SimpleNamespace(async_all=_get_states))
    handler = SimpleNamespace(options={}, hass=fake_hass)

    schema = await config_flow.general_config_schema(handler, hass=fake_hass)

    schema_mapping = getattr(schema, "schema", None) or {}

    def opt_label(o):
        if isinstance(o, dict):
            return o.get("label")
        return getattr(o, "label", None)

    found_select = False
    placeholder_found = False
    for val in schema_mapping.values():
        if isinstance(val, config_flow.selector.SelectSelector):
            found_select = True
            cfg = getattr(val, "config", {})
            opts = (
                cfg.get("options")
                if isinstance(cfg, dict)
                else getattr(cfg, "options", [])
            )
            if any(opt_label(o) == "No persons available" for o in (opts or [])):
                placeholder_found = True

    assert found_select, "Expected a SelectSelector fallback for assignee"
    assert (
        placeholder_found
    ), "Expected the placeholder option in SelectSelector when person fetch fails"
