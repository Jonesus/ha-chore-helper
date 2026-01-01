"""Tests for config flow assignee selector fallback behavior."""

from types import SimpleNamespace

import pytest


from custom_components.chore_helper import config_flow


@pytest.mark.asyncio
async def test_assignee_dropdown_fallback_in_config() -> None:
    """Ensure a dropdown is built from hass.auth users for assignee selection."""

    user1 = SimpleNamespace(id="u1", name="Alice", is_system=False, is_active=True)
    user2 = SimpleNamespace(id="u2", name="Bob", is_system=False, is_active=True)

    async def _get_users():
        return [user1, user2]

    fake_hass = SimpleNamespace(auth=SimpleNamespace(async_get_users=_get_users))
    handler = SimpleNamespace(options={}, hass=fake_hass)

    schema = await config_flow.general_config_schema(handler, hass=fake_hass)

    # Search schema for a SelectSelector whose options include our test users
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
            if any(opt_value(o) == "u1" for o in (opts or [])):
                found = True
                break

    assert found, "Assignee SelectSelector with user options not found in config schema"


@pytest.mark.asyncio
async def test_assignee_dropdown_fallback_in_options() -> None:
    """Ensure the options flow provides a dropdown built from hass.auth users."""

    user1 = SimpleNamespace(id="u1", name="Alice", is_system=False, is_active=True)
    user2 = SimpleNamespace(id="u2", name="Bob", is_system=False, is_active=True)

    async def _get_users():
        return [user1, user2]

    fake_hass = SimpleNamespace(auth=SimpleNamespace(async_get_users=_get_users))
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
            if any(opt_value(o) == "u1" for o in (opts or [])):
                found = True
                break

    assert (
        found
    ), "Assignee SelectSelector with user options not found in options schema"


@pytest.mark.asyncio
async def test_assignee_select_when_user_fetch_fails() -> None:
    """If fetching users fails, still provide a SelectSelector with a placeholder option."""

    async def _get_users():
        raise Exception("nope")

    fake_hass = SimpleNamespace(auth=SimpleNamespace(async_get_users=_get_users))
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
            if any(opt_label(o) == "No users available" for o in (opts or [])):
                placeholder_found = True

    assert found_select, "Expected a SelectSelector fallback for assignee"
    assert (
        placeholder_found
    ), "Expected the placeholder option in SelectSelector when user fetch fails"
