# rubox/filters.py

from typing import Callable, Any, Optional, Union, List
from dataclasses import dataclass
import logging # اضافه کردن لاگینگ

logger = logging.getLogger(__name__) # تعریف لاگر

@dataclass
class Filter:
    condition: Callable[[Any], bool]

    def __call__(self, message: dict) -> bool:
        return self.condition(message)

    def __and__(self, other):
        return Filter(lambda m: self(m) and other(m))

    def __or__(self, other):
        return Filter(lambda m: self(m) or other(m))

def commands(values: Union[str, List[str]]) -> Filter:
    if isinstance(values, str):
        values = [values]

    def check_command(message: dict) -> bool:
        message_text = message.get("text", "").strip()
        if not message_text.startswith("/"):
            return False
        
        command_parts = message_text[1:].split(maxsplit=1)
        if not command_parts:
            return False
            
        command = command_parts[0].lower()
        
        normalized_values = [v[1:].lower() if v.startswith('/') else v.lower() for v in values]
        return command in normalized_values
        
    return Filter(check_command)

def text(value: str) -> Filter:
    return Filter(lambda m: m.get("text", "").lower() == value.lower())

def chat_type(value: str) -> Filter:
    return Filter(lambda m: m.get("chat_type", "") == value)

def inline_button_id(value: str) -> Filter:
    return Filter(lambda m: m.get("button_id", "") == value)

def private():
    return Filter(lambda msg: msg.get("sender_type") == "User")

def inline_data(value: str) -> Filter:
    return Filter(lambda m: m.get("data", "") == value)

def location():
    return Filter(lambda msg: "location" in msg)

def sticker():
    return Filter(lambda msg: "sticker" in msg)

def file():
    return Filter(lambda msg: "file" in msg)

def contact():
    return Filter(lambda msg: "contact_message" in msg)

def at_state(state_name: str) -> Filter:
    """
    Args:
        state_name: نام حالت مورد نظر
        
    Returns:
        Filter object
    """
    def check_state(message: dict) -> bool:
        client = message.get('_client')
        if not client or not hasattr(client, 'state_manager'):
            logger.debug(f"Client or state_manager not found in message for at_state filter. Message keys: {message.keys()}")
            return False
        raw_user_id = message.get("chat_id")
        user_id = ""
        if isinstance(raw_user_id, dict):
            user_id = raw_user_id.get("chat_id", "")
        elif raw_user_id is not None:
            user_id = str(raw_user_id)
        
        if not user_id:
            logger.warning(f"Empty user_id received in at_state filter. Raw sender_object_guid: {raw_user_id}. Full message (first 100 chars): {str(message)[:100]}...")
            return False
        
        current_state = client.state_manager.get_state(user_id)
        logger.debug(f"Checking state for user {user_id}: current_state='{current_state}', target_state='{state_name}'")
        return current_state == state_name
    
    return Filter(check_state)

def has_any_state() -> Filter:
    """    
    Returns:
        Filter object
    """
    def check_any_state(message: dict) -> bool:
        client = message.get('_client')
        if not client or not hasattr(client, 'state_manager'):
            logger.debug(f"Client or state_manager not found in message for has_any_state filter. Message keys: {message.keys()}")
            return False
        
        raw_user_id = message.get("sender_object_guid")
        user_id = ""
        if isinstance(raw_user_id, dict):
            user_id = raw_user_id.get("object_guid", "")
        elif raw_user_id is not None:
            user_id = str(raw_user_id)
        
        if not user_id:
            logger.warning(f"Empty user_id received in has_any_state filter. Raw sender_object_guid: {raw_user_id}. Full message (first 100 chars): {str(message)[:100]}...")
            return False
        
        has_state = client.state_manager.has_state(user_id)
        logger.debug(f"Checking any state for user {user_id}: has_state={has_state}")
        return has_state
    
    return Filter(check_any_state)

