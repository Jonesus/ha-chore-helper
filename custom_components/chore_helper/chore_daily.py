"""Entity for a daily chore."""

from .chore import Chore
from .const import LOGGER
from datetime import date
from dateutil.relativedelta import relativedelta
from homeassistant.config_entries import ConfigEntry


class DailyChore(Chore):
    """Entity for a daily chore."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Read parameters specific for Daily Chore Frequency."""
        super().__init__(config_entry)
        config = config_entry.options
        self._period = config.get("period", 1)  # Default to 1 if not provided

    def _find_candidate_date(self, day1: date) -> date | None:
        """Calculate possible date, for every-n-days and after-n-days frequency."""
        schedule_start_date = self._calculate_schedule_start_date()
        day1 = self.calculate_day1(day1, schedule_start_date)

        if schedule_start_date is None or self._period is None:
            LOGGER.error(
                "(%s) Missing schedule_start_date or period configuration.",
                self._attr_name,
            )
            return None

        try:
            remainder = (day1 - schedule_start_date).days % self._period
            if remainder == 0:
                return day1
            offset = self._period - remainder
        except TypeError as error:
            raise ValueError(
                f"({self._attr_name}) Please configure start_date and period "
                "for every-n-days or after-n-days chore frequency."
            ) from error

        candidate_date = day1 + relativedelta(days=offset)
        LOGGER.debug(
            "(%s) Calculated candidate date: day1=%s, schedule_start_date=%s, candidate_date=%s",
            self._attr_name,
            day1,
            schedule_start_date,
            candidate_date,
        )
        return candidate_date
