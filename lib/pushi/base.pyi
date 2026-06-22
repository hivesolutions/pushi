from typing import Any, TypedDict

from appier import API as AppierAPI

from .apn import APNAPI
from .app import AppAPI
from .web import WebAPI
from .smtp import SMTPAPI
from .event import EventAPI
from .messaging import MessagingAPI
from .web_push import WebPushAPI
from .subscription import SubscriptionAPI

BASE_URL: str = ...
BASE_WS_URL: str = ...

class PushiRecord(TypedDict):
    id: int
    instance: str | None

class API(
    AppierAPI,
    APNAPI,
    AppAPI,
    WebAPI,
    SMTPAPI,
    EventAPI,
    MessagingAPI,
    WebPushAPI,
    SubscriptionAPI,
):
    app_id: str | None
    app_key: str | None
    app_secret: str | None
    base_url: str
    token: str | None
    def __init__(self, *args, **kwargs) -> None: ...
    def build(
        self,
        method: str,
        url: str,
        data: Any | None = ...,
        data_j: Any | None = ...,
        data_m: Any | None = ...,
        headers: dict[str, str] | None = ...,
        params: dict[str, Any] | None = ...,
        mime: str | None = ...,
        kwargs: dict[str, Any] | None = ...,
    ) -> None: ...
    def get_token(self) -> str: ...
    def auth_callback(
        self, params: dict[str, object], headers: dict[str, str]
    ) -> None: ...
    def login(self) -> str: ...
    def logout(self) -> None: ...
    def authenticate(self, channel: str, socket_id: str) -> str: ...
