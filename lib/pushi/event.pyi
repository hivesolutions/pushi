from typing import Any, Mapping

class EventAPI(object):
    def create_event(
        self, channel: str, data: Any, event: str = ..., persist: bool = ..., **kwargs
    ) -> Mapping[str, Any]: ...
    def trigger_event(self, *args, **kwargs) -> Mapping[str, Any]: ...
