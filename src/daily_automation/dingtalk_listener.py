"""One-to-one DingTalk Stream bot intake while this computer is online."""

from __future__ import annotations

import json
import logging
import threading
import asyncio
from pathlib import Path
from urllib.parse import urlparse

import requests

from .campus_service import CampusService
from .password_crypto import PasswordCrypto
from .runtime_lock import runtime_lock


def interpret_message(data: dict) -> tuple[str, str, str, bool]:
    """Return title, body, URL, needs_review. Never assume a merged forward is complete."""
    kind = str(data.get("msgtype", "")).lower()
    forward_content = data.get("content", {})
    if isinstance(forward_content, str):
        try:
            forward_content = json.loads(forward_content)
        except ValueError:
            forward_content = {}
    if not isinstance(forward_content, dict):
        forward_content = {}
    if str(data.get("isForwardMsg", "0")) == "1" and forward_content.get("chatRecord"):
        summary = str(forward_content.get("summary", "合并转发消息"))
        return "合并转发消息", summary, "", True
    if kind == "text":
        text = data.get("text", {})
        body = text.get("content", "") if isinstance(text, dict) else str(text)
        body = str(body or "").strip()
        return body[:80] or "空白消息", body, "", not bool(body)
    if kind in {"link", "markdown"}:
        content = data.get("content", {})
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except ValueError:
                content = {"text": content}
        if not isinstance(content, dict):
            return "待补充的钉钉通知", "无法读取消息文字，请补充原文。", "", True
        title = str(content.get("title") or "转发链接")
        body = str(content.get("text") or content.get("content") or title)
        url = str(content.get("messageUrl") or content.get("url") or "")
        return title[:80], body, url, not bool(body or url)
    return "待补充的钉钉通知", f"收到 {kind or '未知'} 类型消息，请粘贴文字或链接。", "", True


def record_message(service: CampusService, data: dict, allowed: set[str]) -> str:
    if str(data.get("conversationType", "")) != "1":
        return "请私聊机器人转发通知。"
    sender = str(data.get("senderStaffId") or data.get("senderId") or "")
    if allowed and sender not in allowed:
        return "此账号尚未获准向个人日程收件箱转发。"
    title, body, url, review = interpret_message(data)
    if not body and not url:
        return "需补充原文：请发送通知文字或链接。"
    # Unsupported callbacks can be retried: retain their message identity.
    external_id = str(data.get("msgId")) if review and data.get("msgId") else None
    notice_id, _ = service.ingest("dingtalk", title, body, url, external_id=external_id)
    if review:
        service.store.set_analysis(notice_id, summary=title, action="", review_state="review")
        return "已记录为待核对，需补充原文：请在本地应用补充文字或链接。"
    return "已记录，下次汇总生成待办；排入计划需要你确认。"


def create_stream_client(client_id: str, client_secret: str):
    import dingtalk_stream
    quiet = logging.getLogger("daily_automation.dingtalk_sdk")
    quiet.handlers = [logging.NullHandler()]
    quiet.propagate = False
    quiet.setLevel(logging.CRITICAL + 1)

    class BoundedClient(dingtalk_stream.DingTalkStreamClient):
        def open_connection(self):
            # The SDK's default request has no timeout and logs connection tickets.
            try:
                response = requests.post(self.OPEN_CONNECTION_API, json={
                    "clientId": client_id, "clientSecret": client_secret,
                    "subscriptions": [{"type": "CALLBACK", "topic": topic} for topic in self.callback_handler_map],
                    "ua": "daily-automation-campus",
                }, timeout=20)
                response.raise_for_status()
                result = response.json()
                endpoint = urlparse(result.get("endpoint", ""))
                if endpoint.scheme != "wss" or not (endpoint.hostname or "").endswith(".dingtalk.com") or not result.get("ticket"):
                    raise ValueError("连接响应无效")
                return result
            except (requests.RequestException, ValueError):
                return None

    return BoundedClient(dingtalk_stream.Credential(client_id, client_secret), logger=quiet)


def _reply(data: dict, text: str) -> bool:
    webhook = str(data.get("sessionWebhook") or "")
    parsed = urlparse(webhook)
    if parsed.scheme != "https" or parsed.hostname not in {"oapi.dingtalk.com", "api.dingtalk.com"}:
        return False
    try:
        response = requests.post(webhook, json={"msgtype": "text", "text": {"content": text}}, timeout=15)
        response.raise_for_status()
        return response.json().get("errcode", 0) == 0
    except (requests.RequestException, ValueError):
        return False


def listen(runtime_dir: Path, config: dict):
    try:
        import dingtalk_stream
        from dingtalk_stream import AckMessage
    except ImportError as exc:
        raise RuntimeError("请先安装 dingtalk-stream 依赖") from exc

    settings = config.get("dingtalk", {})
    client_id = settings.get("client_id", "").strip()
    encrypted = settings.get("client_secret", "")
    client_secret = PasswordCrypto(runtime_dir).decrypt(encrypted) if encrypted.startswith("fernet:") else ""
    if not client_id or not client_secret or client_secret == encrypted:
        raise RuntimeError("请先在网页端配置钉钉应用 Client ID 和 Client Secret")
    service = CampusService(runtime_dir, config)
    allowed = set(settings.get("allowed_sender_ids", []))

    class IntakeHandler(dingtalk_stream.ChatbotHandler):
        async def process(self, callback):
            data = callback.data
            try:
                text = await asyncio.to_thread(record_message, service, data, allowed)
            except Exception:
                await asyncio.to_thread(_reply, data, "记录失败，请在本地网页端粘贴补录。")
                return 500, "Record failed"
            if not await asyncio.to_thread(_reply, data, text):
                service.store.set_source_state("dingtalk", "warning", "记录已落盘，但确认回复失败；可在本地收件箱核对")
            return AckMessage.STATUS_OK, "OK"

    client = create_stream_client(client_id, client_secret)
    client.register_callback_handler(dingtalk_stream.chatbot.ChatbotMessage.TOPIC, IntakeHandler())
    stopped = threading.Event()
    def heartbeat():
        while not stopped.is_set():
            ws = client.websocket
            connected = ws is not None and (getattr(ws, "state", None) == 1 or getattr(ws, "closed", True) is False)
            service.store.set_source_state("dingtalk", "ok" if connected else "warning",
                                           "连接正常，可私聊转发" if connected else "正在连接，收到确认回复后才算记录成功")
            stopped.wait(30)
    with runtime_lock(runtime_dir / "locks" / "dingtalk_listener.lock"):
        worker = threading.Thread(target=heartbeat, daemon=True)
        worker.start()
        try:
            client.start_forever()
        finally:
            stopped.set()
            worker.join(timeout=2)
            service.store.set_source_state("dingtalk", "warning", "监听程序已停止，离线转发需补录")
