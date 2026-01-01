"""Tests for the config_flow/options_flow properties on the handler."""

from types import SimpleNamespace

import pytest


from custom_components.chore_helper import config_flow


@pytest.mark.asyncio
async def test_config_flow_user_step_uses_handler_hass() -> None:
    """Ensure the handler's config_flow property captures self.hass for schema builders."""
    # Create an instance and attach a fake hass with a user list
    handler_inst = config_flow.ChoreHelperConfigFlowHandler()

    async def _get_users():
        return [SimpleNamespace(id="u1", name="Alice", is_system=False, is_active=True)]

    handler_inst.hass = SimpleNamespace(
        auth=SimpleNamespace(async_get_users=_get_users)
    )

    # Get the config flow and its "user" step
    flow = handler_inst.config_flow
    assert "user" in flow

    schema_callable = flow["user"].schema

    # Call the schema callable with a minimal SchemaCommonFlowHandler-like object that
    # exposes a parent_handler attribute pointing at the real handler (so the wrapper can
    # access `parent_handler.hass`).
    schema = await schema_callable(
        SimpleNamespace(options={}, parent_handler=handler_inst)
    )

    schema_mapping = getattr(schema, "schema", None) or {}

    found_select = False
    for val in schema_mapping.values():
        if isinstance(val, config_flow.selector.SelectSelector):
            found_select = True
            break

    assert found_select, "Expected a SelectSelector in the user step schema"


@pytest.mark.asyncio
async def test_options_flow_init_step_uses_handler_hass() -> None:
    """Ensure the handler's options_flow property captures self.hass for schema builders."""
    handler_inst = config_flow.ChoreHelperConfigFlowHandler()

    async def _get_users():
        return [SimpleNamespace(id="u1", name="Alice", is_system=False, is_active=True)]

    handler_inst.hass = SimpleNamespace(
        auth=SimpleNamespace(async_get_users=_get_users)
    )

    flow = handler_inst.options_flow
    assert "init" in flow

    schema_callable = flow["init"].schema
    schema = await schema_callable(
        SimpleNamespace(options={}, parent_handler=handler_inst)
    )

    schema_mapping = getattr(schema, "schema", None) or {}

    found_select = False
    for val in schema_mapping.values():
        if isinstance(val, config_flow.selector.SelectSelector):
            found_select = True
            break

    assert found_select, "Expected a SelectSelector in the options init step schema"
