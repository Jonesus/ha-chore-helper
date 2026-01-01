"""Tests for config/options flow schema builders when handler lacks hass."""

from types import SimpleNamespace

import pytest


from custom_components.chore_helper import config_flow


@pytest.mark.asyncio
async def test_general_config_schema_uses_placeholder_when_no_hass() -> None:
    """Ensure the config schema returns a SelectSelector with a placeholder when handler has no hass."""
    handler = SimpleNamespace(options={})

    schema = await config_flow.general_config_schema(handler)

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

    assert found_select
    assert placeholder_found


@pytest.mark.asyncio
async def test_general_options_schema_uses_placeholder_when_no_hass() -> None:
    """Ensure the options schema returns a SelectSelector with a placeholder when handler has no hass."""
    handler = SimpleNamespace(options={})

    schema = await config_flow.general_options_schema(handler)

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

    assert found_select
    assert placeholder_found
