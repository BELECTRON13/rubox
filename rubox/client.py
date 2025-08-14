# rubox/client.py
import aiohttp
import asyncio
import time
import logging
from typing import Callable, Dict, Any, Optional, List, Union, Tuple
from collections import deque
from .filters import Filter
from .keyboard import Button, Keypad, KeypadRow
from .message import Message
from .state_manager import StateManager
from aiohttp import web
import json

# Setup logging
logger = logging.getLogger(__name__)

def has_time_passed(last_time, seconds: int = 5) -> bool:
    try:
        timestamp = int(float(last_time))
        now = time.time()
        return (now - timestamp) > seconds
    except (TypeError, ValueError):
        return False

class ReceiveUpdate:
    def __init__(self, update_id: str, type: str, payload: Dict[str, Any]):
        self.update_id = update_id
        self.type = type
        self.payload = payload

class ReceiveInlineMessage:
    def __init__(self, id: str, chat_id: str, text: str, data: Optional[str] = None, button_id: Optional[str] = None):
        self.id = id
        self.chat_id = chat_id
        self.text = text
        self.data = data
        self.button_id = button_id

class ReceiveQuery:
    def __init__(self, query_id: str, from_id: str, query_type: str, query_data: Dict[str, Any]):
        self.query_id = query_id
        self.from_id = from_id
        self.query_type = query_type
        self.query_data = query_data

class GetSelectionItem:
    def __init__(self, item_id: str, item_name: str):
        self.item_id = item_id
        self.item_name = item_name

class SearchSelectionItems:
    def __init__(self, query: str, items: List[GetSelectionItem]):
        self.query = query
        self.items = items

class Client:
    def __init__(self, token: str, rate_limit: float = 0.5, set_webhook: bool = False, state_expire_after: int = 3600):
        self.token = token
        self.base_url = f"https://botapi.rubika.ir/v3/{self.token}"
        self._handlers: List[tuple[Filter, Callable]] = []
        self._inline_handlers: List[tuple[Filter, Callable]] = []
        self._endpoint_handlers: Dict[str, Callable] = {}
        self.app = web.Application()
        self.runner = None
        self.session = None
        self.running = False
        
        # State Management
        self.state_manager = StateManager(expire_after=state_expire_after)
        
        self.next_offset_id = None
        self.processed_messages = deque(maxlen=10000)
        self.rate_limit = rate_limit
        self.last_request_time = 0
        self.first_get_updates = True
        self.set_webhook = set_webhook
        
        logger.info("Rubika client initialized, set_webhook=%s", set_webhook)

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.stop()

    async def _rate_limit_delay(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

    async def start(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        self.running = True
        # شروع وظیفه پاک‌سازی حالت‌ها
        self.state_manager.start_cleanup_task()
        logger.info("Rubika client started")

    async def stop(self):
        if self.session and not self.session.closed:
            await self.session.close()
        self.running = False
        if self.runner:
            await self.runner.cleanup()
        logger.info("Rubika client stopped")

    def on_message(self, filters: Filter):
        def decorator(func: Callable):
            self._handlers.append((filters, func))
            return func
        return decorator

    def on_inline_message(self, filters: Filter):
        def decorator(func: Callable):
            self._inline_handlers.append((filters, func))
            return func
        return decorator

    def on_endpoint_update(self, endpoint_type: str):
        def decorator(func: Callable):
            self._endpoint_handlers[endpoint_type] = func
            return func
        return decorator
    
    async def _request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        await self._rate_limit_delay()
        url = f"{self.base_url}/{method}"
        
        try:
            async with self.session.post(url, json=params or {}) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.error(f"Request failed: {method} status={resp.status} body={text}")
                    raise aiohttp.ClientResponseError(resp.request_info, resp.history, status=resp.status, message=text)
                
                data = await resp.json()
                logger.debug(f"API response for {method}: {data}")
                
                if data.get("status") != "OK":
                    logger.error(f"API error in {method}: {data}")
                    raise Exception(f"API Error: {data}")
                return data.get("data")
        except Exception as e:
            logger.error(f"Error in _request for {method}: {str(e)}")
            raise

    async def get_me(self):
        return await self._request("getMe")

    async def get_updates(self, limit: int = 100, offset_id: str = "") -> Dict[str, Any]:
        data = {"limit": limit}
        if offset_id:
            data["offset_id"] = offset_id
        return await self._request("getUpdates", data)

    async def updater(self, limit: int = 100, offset_id: str = "") -> List[Dict[str, Any]]:
        data = {"limit": limit}
        updates = []
        
        if offset_id or self.next_offset_id:
            data["offset_id"] = self.next_offset_id if not offset_id else offset_id

        try:
            response = await self._request("getUpdates", data)
            self.next_offset_id = response.get("next_offset_id", self.next_offset_id)
            
            for item in response.get("updates", []):
                update = self._parse_update(item)
                if update:

                    if update.get("type") == "RemovedMessage":
                        continue

                    # Extract timestamp for anti-spam
                    last_time = None
                    if update.get("type") == "NewMessage" and update.get("new_message"):
                        last_time = update["new_message"].get("time")
                    elif update.get("type") == "UpdatedMessage" and update.get("updated_message"):
                        last_time = update["updated_message"].get("time")

                    if last_time and has_time_passed(last_time, 5):
                        continue

                    updates.append(update)

        except Exception as e:
            logger.exception(f"Failed to get updates: {str(e)}")

        if self.first_get_updates:
            self.first_get_updates = False
            return []

        return updates

    def _parse_update(self, item: Dict) -> Optional[Dict[str, Any]]:
        update_type = item.get("type")
        if not update_type:
            logger.debug(f"Skipping update with no type: {item}")
            return None

        chat_id = item.get("chat_id", "")
        
        if update_type == "RemovedMessage":
            return {
                "type": "RemovedMessage",
                "chat_id": chat_id,
                "removed_message_id": str(item.get("removed_message_id", ""))
            }
        elif update_type in ["NewMessage", "UpdatedMessage"]:
            msg_key = "new_message" if update_type == "NewMessage" else "updated_message"
            msg_data = item.get(msg_key)
            if not msg_data:
                logger.debug(f"Skipping {msg_key} with no message data: {item}")
                return None

            msg_data["message_id"] = str(msg_data.get("message_id", ""))
            msg_data["chat_id"] = chat_id
            msg_data["_client"] = self  # اضافه کردن client به message data
            self._detect_chat_type(msg_data, chat_id)
            return {
                "type": update_type,
                "chat_id": chat_id,
                msg_key: msg_data
            }
        elif update_type == "InlineMessage":
            inline_msg_data = item.get("inline_message", item.copy()) 
            inline_msg_data["chat_id"] = chat_id
            inline_msg_data["_client"] = self  # اضافه کردن client به inline message data
            self._detect_chat_type(inline_msg_data, chat_id)
            
            aux_data = inline_msg_data.get("aux_data", {})
            if "button_id" in aux_data:
                inline_msg_data["button_id"] = aux_data["button_id"]

            return {
                "type": "InlineMessage",
                "chat_id": chat_id,
                "inline_message": inline_msg_data
            }
        else:
            logger.debug(f"Unhandled update type: {update_type}, data: {item}")
            return item

    async def process_update(self, update: Dict[str, Any]):

        update_type = update.get("type")
        message_id = self._extract_message_id(update)

        if message_id and message_id in self.processed_messages:
            logger.debug(f"Skipping processed update ({update_type}): {message_id}")
            return

        if message_id:
            self.processed_messages.append(message_id)

        logger.info(f"Processing update: {update_type}")
        
        try:
            if update_type == "NewMessage":
                msg_data = update.get("new_message", {})
                if msg_data:
                    message = Message(msg_data, self)
                    for filt, handler in self._handlers:
                        if filt(msg_data):
                            if asyncio.iscoroutinefunction(handler):
                                await handler(message)
                            else:
                                handler(message)
                            break
            
            elif update_type == "InlineMessage":
                inline_msg = update.get("inline_message", {})
                if inline_msg:
                    for filt, handler in self._inline_handlers:
                        if filt(inline_msg):
                            if asyncio.iscoroutinefunction(handler):
                                await handler(inline_msg)
                            else:
                                handler(inline_msg)
                            break

        except Exception as e:
            logger.exception(f"Error processing update {update_type}: {str(e)}")

    def _extract_message_id(self, update: Dict[str, Any]) -> Optional[str]:
        update_type = update.get("type")
        
        if update_type == "RemovedMessage":
            return update.get("removed_message_id")
        elif update_type == "NewMessage":
            msg = update.get("new_message", {})
            return msg.get("message_id")
        elif update_type == "UpdatedMessage":
            msg = update.get("updated_message", {})
            return msg.get("message_id")
        elif update_type == "InlineMessage":
            inline_msg = update.get("inline_message", {})
            return inline_msg.get("id")
        
        return None

    async def send_message(self, chat_id: str, text: str, chat_keypad: Optional[Keypad] = None, inline_keypad: Optional[Keypad] = None, disable_notification: Optional[bool] = False, reply_to_message_id: Optional[str] = None):
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_notification": disable_notification
        }
        if chat_keypad:
            payload["chat_keypad"] = chat_keypad.to_dict()
            payload["chat_keypad_type"] = "New"
        if inline_keypad:
            payload["inline_keypad"] = inline_keypad.to_dict()
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        return await self._request("sendMessage", payload)
    
    async def get_chat(self, chat_id: str):
        return await self._request("getChat", {"chat_id": chat_id})
    
    async def forward_message(self, from_chat_id: str, message_id: str, to_chat_id: str, disable_notification: bool):
        return await self._request("forwardMessage", {
            "from_chat_id": from_chat_id,
            "message_id": message_id,
            "to_chat_id": to_chat_id,
            "disable_notification": disable_notification
        })
    
    async def send_poll(self, chat_id: str, question: str, options: list[str], chat_keypad: Optional[Keypad] = None, inline_keypad: Optional[Keypad] = None, disable_notification: Optional[bool] = False, reply_to_message_id: Optional[str] = None):
        payload = {
            "chat_id": chat_id,
            "question": question,
            "options": options,
            "disable_notification": disable_notification
        }
        if chat_keypad:
            payload["chat_keypad"] = chat_keypad.to_dict()
            payload["chat_keypad_type"] = "New"
        if inline_keypad:
            payload["inline_keypad"] = inline_keypad.to_dict()
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        return await self._request("sendPoll", payload)
    
    async def send_location(self, chat_id: str, latitude: str, longitude: str, chat_keypad: Optional[Keypad] = None, disable_notification: Optional[bool] = False, inline_keypad: Optional[Keypad] = None, reply_to_message_id: Optional[str] = None):
        payload = {
            "chat_id": chat_id,
            "latitude": latitude,
            "longitude": longitude,
            "disable_notification": disable_notification
        }
        if chat_keypad:
            payload["chat_keypad"] = chat_keypad.to_dict()
            payload["chat_keypad_type"] = "New"
        if inline_keypad:
            payload["inline_keypad"] = inline_keypad.to_dict()
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        return await self._request("sendLocation", payload)
    
    async def send_contact(self, chat_id: str, first_name: Optional[str], last_name: Optional[str], phone_number: Optional[str] = None, chat_keypad: Optional[Keypad] = None, disable_notification: Optional[bool] = False, inline_keypad: Optional[Keypad] = None, reply_to_message_id: Optional[str] = None):
        payload = {
            "chat_id": chat_id,
            "first_name": first_name,
            "last_name": last_name,
            "disable_notification": disable_notification
        }
        if phone_number:
            payload["phone_number"] = phone_number
        if chat_keypad:
            payload["chat_keypad"] = chat_keypad.to_dict()
            payload["chat_keypad_type"] = "New"
        if inline_keypad:
            payload["inline_keypad"] = inline_keypad.to_dict()
        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id
        return await self._request("sendContact", payload)
    
    async def edit_message_text(self, chat_id: str, message_id: str, text: str, chat_keypad: Optional[Keypad] = None, inline_keypad: Optional[Keypad] = None):
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text
        }
        if chat_keypad:
            payload["chat_keypad"] = chat_keypad.to_dict()
            payload["chat_keypad_type"] = "New"
        if inline_keypad:
            payload["inline_keypad"] = inline_keypad.to_dict()
        return await self._request("editMessageText", payload)
    
    async def edit_message_keypad(self, chat_id: str, message_id: str, chat_keypad: Optional[Keypad] = None, inline_keypad: Optional[Keypad] = None):
        payload = {
            "chat_id": chat_id,
            "message_id": message_id
        }
        if chat_keypad:
            payload["chat_keypad"] = chat_keypad.to_dict()
            payload["chat_keypad_type"] = "New"
        if inline_keypad:
            payload["inline_keypad"] = inline_keypad.to_dict()
        return await self._request("editMessageKeypad", payload)
    
    async def delete_message(self, chat_id: str, message_id: str):
        return await self._request("deleteMessage", {
            "chat_id": chat_id,
            "message_id": message_id
        })
    
    async def remove_chat_keypad(self, chat_id: str):
        return await self._request("editChatKeypad", {
            "chat_id": chat_id,
            "chat_keypad_type": "Removed"
        })
    
    async def edit_chat_keypad(self, chat_id: str, chat_keypad: Keypad):
        return await self._request("editChatKeypad", {
            "chat_id": chat_id,
            "chat_keypad": chat_keypad.to_dict(),
            "chat_keypad_type": "New"
        })

    async def update_bot_endpoints(self, url: str, endpoint_type: str):
        return await self._request("updateBotEndpoints", {
            "url": url,
            "type": endpoint_type
        })
    
    async def _handle_endpoint_update(self, request: web.Request):
        if request.method != "POST":
            logger.error(f"Invalid method: {request.method}")
            return web.Response(status=405, text="Method Not Allowed")

        try:
            data = await request.json()
            logger.debug(f"Webhook payload for {request.path}: {json.dumps(data, ensure_ascii=False)}")

            updates = []

            if "inline_message" in data:
                inline_msg_data = data["inline_message"]
                inline_msg_data["chat_id"] = data.get("chat_id", inline_msg_data.get("chat_id", ""))
                inline_msg_data["_client"] = self
                self._detect_chat_type(inline_msg_data, inline_msg_data["chat_id"])
                
                aux_data = inline_msg_data.get("aux_data", {})
                if "button_id" in aux_data:
                    inline_msg_data["button_id"] = aux_data["button_id"]

                updates.append({
                    "type": "InlineMessage",
                    "chat_id": inline_msg_data["chat_id"],
                    "inline_message": inline_msg_data
                })
            elif "update" in data:
                update_data = data["update"]
                if update_data.get("type") == "InlineMessage":
                    inline_msg_data = update_data.get("inline_message", update_data.copy())
                    inline_msg_data["chat_id"] = update_data.get("chat_id", inline_msg_data.get("chat_id", ""))
                    inline_msg_data["_client"] = self
                    self._detect_chat_type(inline_msg_data, inline_msg_data["chat_id"])

                    aux_data = inline_msg_data.get("aux_data", {})
                    if "button_id" in aux_data:
                        inline_msg_data["button_id"] = aux_data["button_id"]

                    updates.append({
                        "type": "InlineMessage",
                        "chat_id": inline_msg_data["chat_id"],
                        "inline_message": inline_msg_data
                    })
                else:
                    parsed_update = self._parse_update(update_data)
                    if parsed_update:
                        updates.append(parsed_update)

            for update in updates:
                asyncio.create_task(self.process_update(update))

            return web.json_response({"status": "OK"})
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook request")
            return web.json_response({"status": "ERROR", "error": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.error(f"Webhook error for {request.path}: {str(e)}")
            return web.json_response({"status": "ERROR", "error": str(e)}, status=500)

    async def run(self, webhook_url: Optional[str] = None, path: Optional[str] = '/webhook', host: str = "0.0.0.0", port: int = 8080):
        self.set_webhook = bool(webhook_url)
        await self.start()
        
        if self.set_webhook:
            app = web.Application()
            webhook_base = path.rstrip('/')
            app.router.add_post(f"{webhook_base}", self._handle_endpoint_update)
            app.router.add_post(f"{webhook_base}/receiveUpdate", self._handle_endpoint_update)
            app.router.add_post(f"{webhook_base}/receiveInlineMessage", self._handle_endpoint_update)
            
            webhook_url = f"{webhook_url.rstrip('/')}{webhook_base}"
            
            for endpoint_type in ["ReceiveUpdate", "ReceiveInlineMessage"]:
                try:
                    response = await self.update_bot_endpoints(webhook_url, endpoint_type)
                    logger.info(f"Webhook set for {endpoint_type} to {webhook_url}: {response}")
                except Exception as e:
                    logger.error(f"Failed to set webhook for {endpoint_type}: {str(e)}")
            
            self.runner = web.AppRunner(app)
            await self.runner.setup()
            site = web.TCPSite(self.runner, host, port)
            await site.start()
            logger.info(f"Webhook server running at http://{host}:{port}{webhook_base}")
            print(f"---Webhook activated at (http://{host}:{port}{webhook_base})---")
            
            try:
                while self.running:
                    await asyncio.sleep(1)
            finally:
                await self.stop()
        else:
            get_info = await self.get_me()
            print(f"---Client({get_info.get('bot').get('username')}) is ready---")
            logger.info("Starting polling mode")
            
            while self.running:
                try:
                    updates = await self.updater(limit=100)
                    for update in updates:
                        logger.info(f"Processing polled update: {update.get('type')}")
                        asyncio.create_task(self.process_update(update))
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Polling error: {str(e)}")
                    await asyncio.sleep(2)

    def _detect_chat_type(self, msg: dict, chat_id: str):
        """تشخیص نوع چت"""
        if chat_id.startswith("u0"):  # User
            msg["chat_type"] = "User"
        elif chat_id.startswith("g0"):  # Group
            msg["chat_type"] = "Group"
        elif chat_id.startswith("c0"):  # Channel
            msg["chat_type"] = "Channel"
        else:
            msg["chat_type"] = "Unknown"