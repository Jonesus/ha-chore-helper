"""Adds config flow for Chore Helper."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast, TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.helpers.schema_config_entry_flow import SchemaCommonFlowHandler

import voluptuous as vol
from homeassistant.const import ATTR_HIDDEN, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowError,
    SchemaFlowFormStep,
    SchemaFlowMenuStep,
    SchemaOptionsFlowHandler,
)

from . import const, helpers
from .const import LOGGER


async def _validate_config(
    handler: SchemaConfigFlowHandler | SchemaOptionsFlowHandler,
    data: Any,
    hass: Any | None = None,
) -> Any:
    """Validate config."""
    if const.CONF_DAY_OF_MONTH in data and data[const.CONF_DAY_OF_MONTH] < 1:
        data[const.CONF_DAY_OF_MONTH] = None

    if const.CONF_DATE in data:
        if (
            data[const.CONF_DATE] == "0"
            or data[const.CONF_DATE] == "0/0"
            or data[const.CONF_DATE] == ""
        ):
            data[const.CONF_DATE] = None
        else:
            try:
                helpers.month_day_text(data[const.CONF_DATE])
            except vol.Invalid as exc:
                raise SchemaFlowError("month_day") from exc

    if (
        const.CONF_WEEKDAY_ORDER_NUMBER in data
        and int(data[const.CONF_WEEKDAY_ORDER_NUMBER]) == 0
    ):
        data[const.CONF_WEEKDAY_ORDER_NUMBER] = None

    if const.CONF_CHORE_DAY in data and data[const.CONF_CHORE_DAY] == "0":
        data[const.CONF_CHORE_DAY] = None

    # Validate provided assignee user exists (if provided)
    if const.CONF_ASSIGNEE_USER in data and data[const.CONF_ASSIGNEE_USER]:
        # Prefer explicit hass provided by calling code, else try handler.hass
        hass_instance = hass if hass is not None else getattr(handler, "hass", None)
        if hass_instance is None:
            # Can't validate without hass; raise schema error to force user correction
            raise SchemaFlowError("assignee_user")
        try:
            await hass_instance.auth.async_get_user(data[const.CONF_ASSIGNEE_USER])  # type: ignore[attr-defined]
        except Exception:
            raise SchemaFlowError("assignee_user")

    return data


def required(
    key: str, options: dict[str, Any], default: Any | None = None
) -> vol.Required:
    """Return vol.Required."""
    if isinstance(options, dict) and key in options:
        suggested_value = options[key]
    elif default is not None:
        suggested_value = default
    else:
        return vol.Required(key)
    return vol.Required(key, description={"suggested_value": suggested_value})


def optional(
    key: str, options: dict[str, Any], default: Any | None = None
) -> vol.Optional:
    """Return vol.Optional."""
    if isinstance(options, dict) and key in options:
        suggested_value = options[key]
    elif default is not None:
        suggested_value = default
    else:
        return vol.Optional(key)
    return vol.Optional(key, description={"suggested_value": suggested_value})


def general_schema_definition(
    handler: SchemaConfigFlowHandler | SchemaOptionsFlowHandler,
) -> Mapping[str, Any]:
    """Create general schema."""
    # Assignee selection will be built dynamically from hass.auth users at runtime
    schema = {
        required(
            const.CONF_FREQUENCY, handler.options, const.DEFAULT_FREQUENCY
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(options=const.FREQUENCY_OPTIONS)
        ),
        optional(
            const.CONF_ICON_NORMAL, handler.options, const.DEFAULT_ICON_NORMAL
        ): selector.IconSelector(),
        optional(
            const.CONF_ICON_TOMORROW, handler.options, const.DEFAULT_ICON_TOMORROW
        ): selector.IconSelector(),
        optional(
            const.CONF_ICON_TODAY, handler.options, const.DEFAULT_ICON_TODAY
        ): selector.IconSelector(),
        optional(
            const.CONF_ICON_OVERDUE, handler.options, const.DEFAULT_ICON_OVERDUE
        ): selector.IconSelector(),
        optional(
            const.CONF_FORECAST_DATES, handler.options, const.DEFAULT_FORECAST_DATES
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0,
                max=100,
                mode=selector.NumberSelectorMode.BOX,
                step=1,
            )
        ),
        optional(ATTR_HIDDEN, handler.options, False): bool,
        optional(const.CONF_MANUAL, handler.options, False): bool,
        optional(
            const.CONF_SHOW_OVERDUE_TODAY,
            handler.options,
            const.DEFAULT_SHOW_OVERDUE_TODAY,
        ): bool,
        optional(
            const.CONF_AUTO_ASSIGN, handler.options, const.DEFAULT_AUTO_ASSIGN
        ): bool,
    }

    return schema


async def general_config_schema(
    handler: SchemaConfigFlowHandler | SchemaOptionsFlowHandler,
    hass: Any | None = None,
) -> vol.Schema:
    """Generate config schema.

    The optional `hass` argument allows callers (e.g., the config flow handler) to
    provide the Home Assistant instance explicitly. This avoids relying on
    `handler.hass`, which may not exist for some schema handlers.
    """
    schema_obj = {required(CONF_NAME, handler.options): selector.TextSelector()}
    schema_obj.update(general_schema_definition(handler))

    # Always expose an assignee dropdown. When possible, populate it from hass.auth users;
    # otherwise provide a single placeholder option so the UI shows a Select.
    placeholder_option = selector.SelectOptionDict(value="", label="No users available")

    hass_instance = hass if hass is not None else getattr(handler, "hass", None)

    if hass_instance is not None:
        try:
            users = await hass_instance.auth.async_get_users()  # type: ignore[attr-defined]
            eligible = [
                u
                for u in users
                if not getattr(u, "is_system", False) and getattr(u, "is_active", True)
            ]
            if eligible:
                options = [
                    selector.SelectOptionDict(value=u.id, label=(u.name or u.id))
                    for u in eligible
                ]
            else:
                options = [placeholder_option]
        except Exception as e:
            LOGGER.error("Error fetching users for assignee selector: %s", e)
            options = [placeholder_option]
    else:
        options = [placeholder_option]

    schema_obj[optional(const.CONF_ASSIGNEE_USER, handler.options)] = (
        selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=options, mode=selector.SelectSelectorMode.DROPDOWN
            )
        )
    )

    return vol.Schema(schema_obj)


async def general_options_schema(
    handler: SchemaConfigFlowHandler | SchemaOptionsFlowHandler,
    hass: Any | None = None,
) -> vol.Schema:
    """Generate options schema.

    The optional `hass` argument allows callers (e.g., the options flow handler) to
    provide the Home Assistant instance explicitly.
    """
    schema_mapping = dict(general_schema_definition(handler))

    # Always expose an assignee dropdown. When possible, populate it from hass.auth users;
    # otherwise provide a single placeholder option so the UI shows a Select.
    placeholder_option = selector.SelectOptionDict(value="", label="No users available")

    hass_instance = hass if hass is not None else getattr(handler, "hass", None)

    if hass_instance is not None:
        try:
            users = await hass_instance.auth.async_get_users()  # type: ignore[attr-defined]
            eligible = [
                u
                for u in users
                if not getattr(u, "is_system", False) and getattr(u, "is_active", True)
            ]
            if eligible:
                options = [
                    selector.SelectOptionDict(value=u.id, label=(u.name or u.id))
                    for u in eligible
                ]
            else:
                options = [placeholder_option]
        except Exception as e:
            LOGGER.error("Error fetching users for assignee selector: %s", e)
            options = [placeholder_option]
    else:
        options = [placeholder_option]

    schema_mapping[optional(const.CONF_ASSIGNEE_USER, handler.options)] = (
        selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=options, mode=selector.SelectSelectorMode.DROPDOWN
            )
        )
    )

    return vol.Schema(schema_mapping)


async def detail_config_schema(
    handler: SchemaConfigFlowHandler | SchemaOptionsFlowHandler,
) -> vol.Schema:
    """Generate options schema."""
    options_schema: dict[vol.Optional | vol.Required, Any] = {}
    frequency = handler.options[const.CONF_FREQUENCY]

    if frequency not in const.BLANK_FREQUENCY:
        if frequency in (
            const.DAILY_FREQUENCY
            + const.WEEKLY_FREQUENCY
            + const.MONTHLY_FREQUENCY
            + const.YEARLY_FREQUENCY
        ):
            uom = {
                "every-n-days": "day(s)",
                "every-n-weeks": "week(s)",
                "every-n-months": "month(s)",
                "every-n-years": "year(s)",
                "after-n-days": "day(s)",
                "after-n-weeks": "week(s)",
                "after-n-months": "month(s)",
                "after-n-years": "year(s)",
            }
            options_schema[required(const.CONF_PERIOD, handler.options)] = (
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=1000,
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement=uom[frequency],
                    )
                )
            )

        if frequency in const.YEARLY_FREQUENCY:
            options_schema[optional(const.CONF_DATE, handler.options)] = (
                selector.TextSelector()
            )

        if frequency in const.MONTHLY_FREQUENCY:
            options_schema[optional(const.CONF_DAY_OF_MONTH, handler.options)] = (
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0,
                        max=31,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                )
            )

            options_schema[
                optional(const.CONF_WEEKDAY_ORDER_NUMBER, handler.options)
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=const.ORDER_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )

            options_schema[optional(const.CONF_FORCE_WEEK_NUMBERS, handler.options)] = (
                selector.BooleanSelector()
            )

            options_schema[optional(const.CONF_DUE_DATE_OFFSET, handler.options)] = (
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=-7,
                        max=7,
                        mode=selector.NumberSelectorMode.SLIDER,
                        unit_of_measurement="day(s)",
                    )
                )
            )

        if frequency in (const.WEEKLY_FREQUENCY + const.MONTHLY_FREQUENCY):
            options_schema[optional(const.CONF_CHORE_DAY, handler.options)] = (
                selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=const.WEEKDAY_OPTIONS,
                    )
                )
            )

        if frequency in const.WEEKLY_FREQUENCY:
            options_schema[
                required(
                    const.CONF_FIRST_WEEK, handler.options, const.DEFAULT_FIRST_WEEK
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=52,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="weeks",
                )
            )

        if frequency not in const.YEARLY_FREQUENCY:
            options_schema[
                optional(
                    const.CONF_FIRST_MONTH, handler.options, const.DEFAULT_FIRST_MONTH
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(options=const.MONTH_OPTIONS)
            )
            options_schema[
                optional(
                    const.CONF_LAST_MONTH, handler.options, const.DEFAULT_LAST_MONTH
                )
            ] = selector.SelectSelector(
                selector.SelectSelectorConfig(options=const.MONTH_OPTIONS)
            )

        options_schema[
            required(const.CONF_START_DATE, handler.options, helpers.now().date())
        ] = selector.DateSelector()

    return vol.Schema(options_schema)


async def choose_details_step(_: dict[str, Any]) -> str:
    """Return next step_id for options flow."""
    return "detail"


def _schema_with_parent_hass(schema_func):
    """Wrap a schema function so it extracts hass from the parent handler."""

    async def _wrapped(handler: SchemaCommonFlowHandler) -> vol.Schema | None:  # type: ignore[name-defined]
        hass_instance = getattr(handler.parent_handler, "hass", None)
        return await schema_func(handler, hass=hass_instance)

    return _wrapped


async def _validate_with_parent_hass(
    handler: SchemaCommonFlowHandler, data: dict[str, Any]
) -> dict[str, Any]:  # type: ignore[name-defined]
    """Validate user input using hass from parent handler."""

    hass_instance = getattr(handler.parent_handler, "hass", None)
    return await _validate_config(handler, data, hass=hass_instance)


# Module-level flow definitions (required at class creation time)
CONFIG_FLOW: dict[str, SchemaFlowFormStep | SchemaFlowMenuStep] = {
    "user": SchemaFlowFormStep(
        _schema_with_parent_hass(general_config_schema), next_step=choose_details_step
    ),
    "detail": SchemaFlowFormStep(
        detail_config_schema, validate_user_input=_validate_with_parent_hass
    ),
}

OPTIONS_FLOW: dict[str, SchemaFlowFormStep | SchemaFlowMenuStep] = {
    "init": SchemaFlowFormStep(
        _schema_with_parent_hass(general_options_schema), next_step=choose_details_step
    ),
    "detail": SchemaFlowFormStep(
        detail_config_schema, validate_user_input=_validate_with_parent_hass
    ),
}


# mypy: ignore-errors
class ChoreHelperConfigFlowHandler(SchemaConfigFlowHandler, domain=const.DOMAIN):
    """Handle a config or options flow for Chore Helper."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW
    VERSION = const.CONFIG_VERSION

    @callback
    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title.

        The options parameter contains config entry options, which is the union of user
        input from the config flow steps.
        """
        return cast(str, options["name"]) if "name" in options else ""
