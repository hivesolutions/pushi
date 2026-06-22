from typing import Any, Mapping, NotRequired, Sequence, TypedDict, Unpack

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

class SendParams(TypedDict):
    apn_tokens: NotRequired[str | Sequence[str]]
    apn_message: NotRequired[Mapping[str, Any] | str]
    email_to: NotRequired[str | Sequence[str]]
    email_subject: NotRequired[str]
    email_body: NotRequired[str]
    email_html: NotRequired[bool]
    webhook_urls: NotRequired[str | Sequence[str]]
    webhook_headers: NotRequired[Mapping[str, str]]
    webhook_method: NotRequired[str]
    web_push_subscriptions: NotRequired[Sequence[WebPushSubscription]]
    web_push_message: NotRequired[Mapping[str, Any] | str]

class APNParams(TypedDict):
    key_data: NotRequired[str]
    cer_data: NotRequired[str]
    sandbox: NotRequired[bool]

class EmailParams(TypedDict):
    smtp_host: NotRequired[str]
    smtp_port: NotRequired[int]
    smtp_user: NotRequired[str]
    smtp_password: NotRequired[str]
    smtp_starttls: NotRequired[bool]
    smtp_sender: NotRequired[str]
    html: NotRequired[bool]

class WebhookParams(TypedDict):
    headers: NotRequired[Mapping[str, str]]
    method: NotRequired[str]

class WebPushParams(TypedDict):
    subscriptions: NotRequired[Sequence[WebPushSubscription]]
    endpoint: NotRequired[str]
    p256dh: NotRequired[str]
    auth: NotRequired[str]
    vapid_private_key: NotRequired[str]
    vapid_email: NotRequired[str]

class MessagingAPI(object):
    def send_messaging(
        self,
        adapters: str | Sequence[str],
        data: Mapping[str, Any] | None = ...,
        **kwargs: Unpack[SendParams]
    ) -> Mapping[str, MessagingResult]: ...
    def send_messaging_apn(
        self,
        tokens: str | Sequence[str],
        message: Mapping[str, Any] | str,
        **kwargs: Unpack[APNParams]
    ) -> MessagingResult: ...
    def send_messaging_email(
        self,
        to: str | Sequence[str],
        subject: str,
        body: str,
        **kwargs: Unpack[EmailParams]
    ) -> MessagingResult: ...
    def send_messaging_webhook(
        self,
        urls: str | Sequence[str],
        data: Mapping[str, Any] | str,
        **kwargs: Unpack[WebhookParams]
    ) -> MessagingResult: ...
    def send_messaging_web_push(
        self,
        message: Mapping[str, Any] | str | None = ...,
        **kwargs: Unpack[WebPushParams]
    ) -> MessagingResult: ...
