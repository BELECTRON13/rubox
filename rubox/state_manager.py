# rubox/state_manager.py
from typing import Dict, Any, Optional
import time
import asyncio
import logging

logger = logging.getLogger(__name__)

class StateManager:
    def __init__(self, expire_after: int = 3600):  # 1 hour default expiry
        """
        مدیریت حالت‌های کاربران
        
        Args:
            expire_after: زمان انقضا حالت به ثانیه (پیش‌فرض: 1 ساعت)
        """
        self.states: Dict[str, Dict[str, Any]] = {}
        self.expire_after = expire_after
        self._cleanup_task = None
    
    def start_cleanup_task(self):
        """شروع وظیفه پاک‌سازی حالت‌های منقضی شده"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_states())
    
    async def _cleanup_expired_states(self):
        """پاک‌سازی حالت‌های منقضی شده هر 5 دقیقه"""
        while True:
            try:
                current_time = time.time()
                expired_users = []
                
                for user_id, state_data in self.states.items():
                    if current_time - state_data.get('created_at', 0) > self.expire_after:
                        expired_users.append(user_id)
                
                for user_id in expired_users:
                    del self.states[user_id]
                    logger.debug(f"Expired state removed for user: {user_id}")
                
                await asyncio.sleep(300)  # 5 minutes
            except Exception as e:
                logger.error(f"Error in cleanup task: {str(e)}")
                await asyncio.sleep(60)
    
    def set_state(self, user_id: str, state: str, data: Optional[Dict[str, Any]] = None):
        """        
        Args:
            user_id: شناسه کاربر
            state: نام حالت
            data: داده‌های اضافی (اختیاری)
        """
        self.states[user_id] = {
            'state': state,
            'data': data or {},
            'created_at': time.time()
        }
        logger.debug(f"State set for user {user_id}: {state}")
    
    def get_state(self, user_id: str) -> Optional[str]:
        """        
        Args:
            user_id: شناسه کاربر
            
        Returns:
            نام حالت یا None در صورت عدم وجود
        """
        state_data = self.states.get(user_id)
        if state_data:
            # بررسی انقضا
            if time.time() - state_data['created_at'] > self.expire_after:
                del self.states[user_id]
                return None
            return state_data['state']
        return None
    
    def get_state_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        دریافت داده‌های حالت کاربر
        
        Args:
            user_id: شناسه کاربر
            
        Returns:
            داده‌های حالت یا None در صورت عدم وجود
        """
        state_data = self.states.get(user_id)
        if state_data:
            # بررسی انقضا
            if time.time() - state_data['created_at'] > self.expire_after:
                del self.states[user_id]
                return None
            return state_data.get('data', {})
        return None
    
    def clear_state(self, user_id: str):
        """
        پاک کردن حالت کاربر
        
        Args:
            user_id: شناسه کاربر
        """
        if user_id in self.states:
            del self.states[user_id]
            logger.debug(f"State cleared for user: {user_id}")
    
    def update_state_data(self, user_id: str, key: str, value: Any):
        """
        به‌روزرسانی داده‌های حالت کاربر
        
        Args:
            user_id: شناسه کاربر
            key: کلید داده
            value: مقدار داده
        """
        if user_id in self.states:
            self.states[user_id]['data'][key] = value
            logger.debug(f"State data updated for user {user_id}: {key} = {value}")
    
    def has_state(self, user_id: str) -> bool:
        """
        بررسی وجود حالت برای کاربر
        
        Args:
            user_id: شناسه کاربر
            
        Returns:
            True اگر کاربر حالت دارد، در غیر این صورت False
        """
        return self.get_state(user_id) is not None
    
    def get_all_users_in_state(self, state: str) -> list[str]:
        """
        دریافت تمام کاربرانی که در حالت مشخص شده هستند
        
        Args:
            state: نام حالت
            
        Returns:
            لیست شناسه کاربران
        """
        users = []
        current_time = time.time()
        expired_users = []
        
        for user_id, state_data in self.states.items():
            if current_time - state_data['created_at'] > self.expire_after:
                expired_users.append(user_id)
                continue
                
            if state_data['state'] == state:
                users.append(user_id)
        
        # پاک کردن حالت‌های منقضی شده
        for user_id in expired_users:
            del self.states[user_id]
        
        return users
    
    def get_stats(self) -> Dict[str, Any]:
        """
        دریافت آمار حالت‌ها
        
        Returns:
            دیکشنری حاوی آمار
        """
        current_time = time.time()
        active_states = {}
        expired_count = 0
        
        for state_data in self.states.values():
            if current_time - state_data['created_at'] > self.expire_after:
                expired_count += 1
                continue
            
            state = state_data['state']
            active_states[state] = active_states.get(state, 0) + 1
        
        return {
            'total_users': len(self.states),
            'active_users': len(self.states) - expired_count,
            'expired_users': expired_count,
            'states_distribution': active_states
        }