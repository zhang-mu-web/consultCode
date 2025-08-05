#!/usr/bin/env python3
"""
用户属性管理系统
使用Redis存储用户信息，动态更新用户属性
"""

import json
import redis
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

class UserManager:
    """用户属性管理器"""
    
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=1):
        """初始化Redis连接"""
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )
        # 这是用于在 Redis 中存储用户信息时的键前缀
        self.user_prefix = "cooking_user:"
        # 这是存储会话信息时的键前缀
        self.session_prefix = "cooking_session:"
    
    def create_user(self, user_id: Optional[str] = None) -> str:
        """创建新用户"""
        # 如果 user_id 为空
        if not user_id:
            # 就生成一个随机的 uuid 作为用户的 id
            user_id = str(uuid.uuid4())
        
        user_data = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "profile": {
                "cooking_level": "beginner",  # 烹饪水平
                "preferences": {
                    "taste": []  # 口味偏好：sweet, savory, spicy, sour
                },
                "allergies": []  # 过敏源
            },
            "current_session": {
                "dish": ""  # 当前做的菜
            },
            "learned_dishes": []  # 已学会的菜品列表
        }
        
        # 存储到Redis
        key = f"{self.user_prefix}{user_id}"
        self.redis_client.set(key, json.dumps(user_data, ensure_ascii=False))
        
        return user_id
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """获取用户信息"""
        key = f"{self.user_prefix}{user_id}"
        data = self.redis_client.get(key)
        if data:
            return json.loads(data)
        return None
    
    def update_user(self, user_id: str, updates: Dict) -> bool:
        """更新用户信息"""
        user_data = self.get_user(user_id)
        if not user_data:
            return False
        
        # 递归更新嵌套字典
        self._update_nested_dict(user_data, updates)
        # 更新最后活跃时间
        user_data["last_active"] = datetime.now().isoformat()
        
        # 存储用户信息
        key = f"{self.user_prefix}{user_id}"
        self.redis_client.set(key, json.dumps(user_data, ensure_ascii=False))
        return True
    
    def _update_nested_dict(self, target: Dict, updates: Dict):
        """递归更新嵌套字典"""
        for key, value in updates.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._update_nested_dict(target[key], value)
            else:
                target[key] = value
    
    def set_current_dish(self, user_id: str, dish: str, taste: str = ""):
        """设置当前做的菜"""
        updates = {
            "current_session": {
                "dish": dish
            }
        }
        
        if taste:
            updates["current_session"]["taste"] = taste
        
        return self.update_user(user_id, updates)
    
    def update_preferences(self, user_id: str, preference_type: str, values: List[str]):
        """更新用户偏好"""
        updates = {
            "profile": {
                "preferences": {
                    preference_type: values
                }
            }
        }
        return self.update_user(user_id, updates)
    
    def update_cooking_level(self, user_id: str, level: str):
        """更新烹饪水平"""
        updates = {
            "profile": {
                "cooking_level": level
            }
        }
        return self.update_user(user_id, updates)
    
    def add_allergy(self, user_id: str, allergy: str):
        """添加过敏原"""
        user_data = self.get_user(user_id)
        if not user_data:
            return False
        
        if "allergies" not in user_data["profile"]:
            user_data["profile"]["allergies"] = []
        
        if allergy not in user_data["profile"]["allergies"]:
            user_data["profile"]["allergies"].append(allergy)
        
        return self.update_user(user_id, user_data)
    
    def get_user_summary(self, user_id: str) -> Dict:
        """获取用户摘要信息"""
        user_data = self.get_user(user_id)
        if not user_data:
            return {}
        
        return {
            "user_id": user_data["user_id"],
            "cooking_level": user_data["profile"]["cooking_level"],
            "taste_preferences": user_data["profile"]["preferences"]["taste"],
            "allergies": user_data["profile"]["allergies"],
            "learned_dishes": user_data.get("learned_dishes", []),  # 已学会的菜品
            "current_dish": user_data["current_session"]["dish"],  # 当前正在做的菜
            "last_active": user_data["last_active"]
        }
    
    def clear_session(self, user_id: str):
        """清除当前会话"""
        updates = {
            "current_session": {
                "dish": ""
            }
        }
        return self.update_user(user_id, updates)
    
    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        key = f"{self.user_prefix}{user_id}"
        return bool(self.redis_client.delete(key))
    
    def get_all_users(self) -> List[str]:
        """获取所有用户ID"""
        pattern = f"{self.user_prefix}*"
        keys = self.redis_client.keys(pattern)
        return [key.replace(self.user_prefix, "") for key in keys]

    def complete_dish(self, user_id: str, completed_dish: str = ""):
        """完成一道菜后更新已学会的菜品列表"""
        user_data = self.get_user(user_id)
        if not user_data:
            return False
        
        # 如果没有指定完成的菜品，使用当前菜品
        if not completed_dish:
            completed_dish = user_data["current_session"]["dish"]
        
        # 确保learned_dishes字段存在
        if "learned_dishes" not in user_data:
            user_data["learned_dishes"] = []
        
        # 将完成的菜品添加到已学会的菜品列表中（如果不存在）
        if completed_dish and completed_dish not in user_data["learned_dishes"]:
            user_data["learned_dishes"].append(completed_dish)
        
        # 更新当前菜品为空，表示可以开始新菜品
        user_data["current_session"]["dish"] = ""
        
        # 更新最后活跃时间
        user_data["last_active"] = datetime.now().isoformat()
        
        # 存储用户信息
        key = f"{self.user_prefix}{user_id}"
        self.redis_client.set(key, json.dumps(user_data, ensure_ascii=False))
        
        print(f"用户 {user_id} 完成菜品: {completed_dish}")
        print(f"已学会的菜品: {user_data['learned_dishes']}")
        return True
    
    def get_user_context_for_prompt(self, user_id: str) -> Dict:
        """获取用户上下文信息用于prompt"""
        user_data = self.get_user(user_id)
        if not user_data:
            return {}
        
        return {
            "cooking_level": user_data["profile"]["cooking_level"],
            "taste_preferences": user_data["profile"]["preferences"]["taste"],
            "allergies": user_data["profile"]["allergies"],
            "current_dish": user_data["current_session"]["dish"],
            "learned_dishes": user_data.get("learned_dishes", [])  # 已学会的菜品
        }
    
    def extract_dish_from_text(self, text: str) -> str:
        """从文本中提取菜品名称（改进版）"""
        import re
        
        # 改进的菜品提取逻辑
        patterns = [
            r"我想做(.+?)(?:吗|呢|啊|？|\?|$)",
            r"(.+?)怎么做",
            r"如何做(.+?)",
            r"(.+?)的做法",
            r"做(.+?)",
            r"(.+?)有哪些做法",
            r"(.+?)怎么做好吃",
            r"(.+?)的烹饪方法"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                candidate = match.strip()
                if candidate and len(candidate) >= 2:
                    # 清理候选菜品名称
                    candidate = re.sub(r'[吗呢啊？\?]', '', candidate)
                    return candidate
        
        # 如果没有匹配到，尝试从文本中提取可能的菜品名称
        # 常见的菜品关键词
        dish_keywords = [
            "鱼", "肉", "鸡", "鸭", "虾", "蟹", "蛋", "豆腐", "青菜", "白菜", 
            "土豆", "茄子", "青椒", "西红柿", "黄瓜", "胡萝卜", "洋葱", "蒜", 
            "姜", "葱", "米饭", "面条", "饺子", "包子", "馒头", "饼", "汤"
        ]
        
        for keyword in dish_keywords:
            if keyword in text:
                # 尝试提取包含关键词的完整菜品名称
                words = text.split()
                for word in words:
                    if keyword in word and len(word) >= 2:
                        return word
        
        return ""

# 全局用户管理器实例
user_manager = UserManager()

def get_user_manager() -> UserManager:
    """获取用户管理器实例"""
    return user_manager 