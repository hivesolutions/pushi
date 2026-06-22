from typing import Any, Mapping, TypedDict

from .base import PushiRecord

class WebPush(PushiRecord):
    endpoint: str
    p256dh: str
    auth: str
    event: str

class WebPushListing(TypedDict):
    subscriptions: list[WebPush]

class WebPushAPI(object):
    def list_web_pushes(
        self, endpoint: str | None = ..., event: str | None = ...
    ) -> WebPushListing: ...
    def create_web_push(
        self,
        endpoint: str,
        p256dh: str,
        auth: str,
        event: str,
        auth_token: str | None = ...,
        unsubscribe: bool = ...,
    ) -> WebPush: ...
    def delete_web_push(
        self, endpoint: str, event: str | None = ..., force: bool = ...
    ) -> Mapping[str, Any]: ...
    def delete_web_pushes(self, endpoint: str) -> Mapping[str, Any]: ...
    def get_vapid_public_key(self) -> Mapping[str, Any]: ...
    def subscribe_web_push(self, *args, **kwargs) -> WebPush: ...
    def unsubscribe_web_push(self, *args, **kwargs) -> Mapping[str, Any]: ...
