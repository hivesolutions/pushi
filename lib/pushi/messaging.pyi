from typing import Any, Mapping, NotRequired, Sequence, TypedDict

class MessagingResult(TypedDict):
    success: bool
    error: NotRequired[str]
    tokens: NotRequired[Sequence[str]]
    recipients: NotRequired[Sequence[str]]
    urls: NotRequired[Sequence[str]]
    method: NotRequired[str]
    endpoints: NotRequired[Sequence[str]]

class WebPushSubscription(TypedDict):
    endpoint: str
    p256dh: str
    auth: str

class MessagingAPI(object):
    def send_messaging(
        self,
        adapters: str | Sequence[str],
        data: Mapping[str, Any] | None = ...,
        **kwargs
    ) -> Mapping[str, MessagingResult]: ...
    def send_messaging_apn(
        self, tokens: str | Sequence[str], message: Mapping[str, Any] | str, **kwargs
    ) -> MessagingResult: ...
    def send_messaging_email(
        self, to: str | Sequence[str], subject: str, body: str, **kwargs
    ) -> MessagingResult: ...
    def send_messaging_webhook(
        self, urls: str | Sequence[str], data: Mapping[str, Any] | str, **kwargs
    ) -> MessagingResult: ...
    def send_messaging_web_push(
        self, message: Mapping[str, Any] | str | None = ..., **kwargs
    ) -> MessagingResult: ...
