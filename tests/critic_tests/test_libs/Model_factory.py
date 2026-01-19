from polyfactory.factories.pydantic_factory import ModelFactory

from critic.models import UptimeMonitorModel


class UptimeMonitorFactory(ModelFactory[UptimeMonitorModel]):
    __model__ = UptimeMonitorModel
