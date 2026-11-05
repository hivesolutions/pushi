from typing import Any, Mapping

from .base import PushiRecord

class App(PushiRecord):
    name: str
    ident: str
    key: str
    secret: str
    apn_sandbox: bool
    apn_key: str | None
    apn_cer: str | None
    apn_auth_key: str | None
    apn_key_id: str | None
    apn_team_id: str | None
    apn_topic: str | None
    vapid_key: str | None
    vapid_email: str | None
    smtp_url: str | None

class AppAPI(object):
    def create_app(self, name: str) -> App: ...
    def update_app(self, app_id: str | None = ..., **kwargs) -> App: ...
