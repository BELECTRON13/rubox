# rubox/message.py
from typing import Optional, TYPE_CHECKING, Dict, Any
from .keyboard import Keypad

if TYPE_CHECKING:
    from .client import Client

class Message:
    def __init__(self, data: dict, client: 'Client'):
        self.client = client
        self._data = data
        
        self.message_id = data.get("message_id", "")
        self.chat_id = data.get("chat_id", "")
        self.text = data.get("text", "")
        self.chat_type = data.get("chat_type", "Unknown")
        self.sender_type = data.get("sender_type", "")
        self.time = data.get("time", "")
        
        sender_info = data.get("sender_object_guid", {})
        if isinstance(sender_info, dict):
            self.sender_id = sender_info.get("object_guid", "")
            self.sender_username = sender_info.get("username", "")
            self.sender_first_name = sender_info.get("first_name", "")
            self.sender_last_name = sender_info.get("last_name", "")
        else:
            self.sender_id = str(sender_info) if sender_info else ""
            self.sender_username = ""
            self.sender_first_name = ""
            self.sender_last_name = ""
        
        self.location = data.get("location")
        self.sticker = data.get("sticker")
        self.file = data.get("file")
        self.contact_message = data.get("contact_message")
        self.poll = data.get("poll")
        
        self.reply_to_message_id = data.get("reply_to_message_id")
    
    def __getitem__(self, key):
        return self._data[key]
    
    def __setitem__(self, key, value):
        self._data[key] = value
    
    def __contains__(self, key):
        return key in self._data
    
    def get(self, key, default=None):
        return self._data.get(key, default)
    
    def keys(self):
        return self._data.keys()
    
    def values(self):
        return self._data.values()
    
    def items(self):
        return self._data.items()
    
    # State Management Methods
    def set_state(self, state: str, data: Optional[Dict[str, Any]] = None):
        """        
        Args:
            state: نام حالت
            data: داده‌های اضافی (اختیاری)
        """
        if self.chat_id:
            self.client.state_manager.set_state(self.chat_id, state, data)
    
    def get_state(self) -> Optional[str]:
        """        
        Returns:
            نام حالت یا None در صورت عدم وجود
        """
        if self.chat_id:
            return self.client.state_manager.get_state(self.chat_id)
        return None
    
    def get_state_data(self) -> Optional[Dict[str, Any]]:
        """        
        Returns:
            داده‌های حالت یا None در صورت عدم وجود
        """
        if self.chat_id:
            return self.client.state_manager.get_state_data(self.chat_id)
        return None
    
    def clear_state(self):
        if self.chat_id:
            self.client.state_manager.clear_state(self.chat_id)
    
    def update_state_data(self, key: str, value: Any):
        """        
        Args:
            key: کلید داده
            value: مقدار داده
        """
        if self.chat_id:
            self.client.state_manager.update_state_data(self.chat_id, key, value)
    
    def has_state(self) -> bool:
        """        
        Returns:
            True اگر کاربر حالت دارد، در غیر این صورت False
        """
        if self.chat_id:
            return self.client.state_manager.has_state(self.chat_id)
        return False
        
    async def reply(self, text: str, 
                   chat_keypad: Optional[Keypad] = None, 
                   inline_keypad: Optional[Keypad] = None, 
                   disable_notification: Optional[bool] = False):
        return await self.client.send_message(
            chat_id=self.chat_id,
            text=text,
            chat_keypad=chat_keypad,
            inline_keypad=inline_keypad,
            disable_notification=disable_notification,
            reply_to_message_id=self.message_id
        )
    
    async def reply_location(self, latitude: str, longitude: str,
                            chat_keypad: Optional[Keypad] = None,
                            inline_keypad: Optional[Keypad] = None,
                            disable_notification: Optional[bool] = False):
        return await self.client.send_location(
            chat_id=self.chat_id,
            latitude=latitude,
            longitude=longitude,
            chat_keypad=chat_keypad,
            inline_keypad=inline_keypad,
            disable_notification=disable_notification,
            reply_to_message_id=self.message_id
        )
    
    async def reply_contact(self, first_name: str, last_name: Optional[str] = None,
                           phone_number: Optional[str] = None,
                           chat_keypad: Optional[Keypad] = None,
                           inline_keypad: Optional[Keypad] = None,
                           disable_notification: Optional[bool] = False):
        return await self.client.send_contact(
            chat_id=self.chat_id,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            chat_keypad=chat_keypad,
            inline_keypad=inline_keypad,
            disable_notification=disable_notification,
            reply_to_message_id=self.message_id
        )
    
    async def reply_poll(self, question: str, options: list[str],
                        chat_keypad: Optional[Keypad] = None,
                        inline_keypad: Optional[Keypad] = None,
                        disable_notification: Optional[bool] = False):
        return await self.client.send_poll(
            chat_id=self.chat_id,
            question=question,
            options=options,
            chat_keypad=chat_keypad,
            inline_keypad=inline_keypad,
            disable_notification=disable_notification,
            reply_to_message_id=self.message_id
        )
    
    async def delete(self):
        return await self.client.delete_message(
            chat_id=self.chat_id,
            message_id=self.message_id
        )
    
    async def forward_to(self, to_chat_id: str, disable_notification: bool = False):
        return await self.client.forward_message(
            from_chat_id=self.chat_id,
            message_id=self.message_id,
            to_chat_id=to_chat_id,
            disable_notification=disable_notification
        )
    
    def __str__(self):
        return f"Message(id={self.message_id}, chat_id={self.chat_id}, text='{self.text[:50]}...')"
    
    def __repr__(self):
        return self.__str__()