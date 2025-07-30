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
    
    def create_user(self, user_id: Optional[str] = None) -> str: # 这里表示函数的返回值类型是字符串
        """创建新用户"""
        # 如果 user_id 为空
        if not user_id:
            # 就生成一个随机的 uuid 作为用户的 id
            user_id = str(uuid.uuid4())
        
        user_data = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(), # 用户的创建时间
            "last_active": datetime.now().isoformat(), # 用户最后的活跃时间
            "profile": { # 用户画像信息
                "name": "",
                "cooking_level": "beginner",  # 烹饪水平
                "preferences": { # 用户偏好
                    "taste": [],  # 口味偏好：sweet, savory, spicy, sour
                    "cuisine": [],  # 菜系偏好：chinese, western, japanese, etc.
                    "dietary": []  # 饮食限制：vegetarian, vegan, gluten_free, etc.
                },
                "allergies": [],  # 过敏源
                "kitchen_equipment": [],  # 可用厨具
                "family_size": 1  # 用餐人数
            },
            "current_session": { # 当前会话信息
                "dish": "",  # 当前做的菜
                "confirmed_ingredients": {},  # 已确认的食材 {ingredient: status}
                "missing_ingredients": [],  # 缺少的食材
                "cooking_steps": [],  # 当前烹饪步骤
                "current_step": 0  # 当前步骤索引
            },
            "cooking_history": [],  # 烹饪历史
            "ingredient_inventory": {}  # 食材库存
        }
        
        # 存储到Redis key = cooking_user : userId
        key = f"{self.user_prefix}{user_id}"
        # setex(key, seconds, value) 设置过期时间   json.dumps：将 python 对象转换为 json 字符串
        self.redis_client.set(key, json.dumps(user_data, ensure_ascii=False))  # 允许中文字符直接存储，不转换为 unicode 编码
        
        return user_id
    
    def get_user(self, user_id: str) -> Optional[Dict]: # 表示函数的返回值是字典类型
        """获取用户信息"""
        # key = cooking_user : userId
        key = f"{self.user_prefix}{user_id}"
        # 根据 key 获取用户信息
        data = self.redis_client.get(key)
        # 如果 data 不为空
        if data:
            # json.loads : 将 data(json 字符串) 转换为 python 对象
            return json.loads(data)
        # 如果 data 为空，就返回 None
        return None
    
    def update_user(self, user_id: str, updates: Dict) -> bool: # 表示函数的返回值是布尔类型
        """更新用户信息"""
        # 首先根据用户 id 获取用户信息
        user_data = self.get_user(user_id)
        # 如果用户信息为空，就返回 False
        if not user_data:
            return False
        
        # 递归更新嵌套字典
        self._update_nested_dict(user_data, updates)
        # 将用户的最后活跃时间更新为当前时间
        user_data["last_active"] = datetime.now().isoformat()
        
        # 再次存储用户信息
        key = f"{self.user_prefix}{user_id}"
        # 永久存储用户信息，没有设置过期时间
        self.redis_client.set(key, json.dumps(user_data, ensure_ascii=False))
        return True
    
    def _update_nested_dict(self, target: Dict, updates: Dict):
        """递归更新嵌套字典"""
        # 遍历 updates 字典中的键值对
        for key, value in updates.items():
            # 如果 target 字典中存在 key 且 value 是字典类型  isinstance(value, dict) 判断 value 是否是字典类型
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # 就递归更新嵌套字典
                self._update_nested_dict(target[key], value)
            else:
                target[key] = value
    
    def update_ingredient_status(self, user_id: str, ingredient: str, status: str):
        """更新食材状态"""
        user_data = self.get_user(user_id)
        if not user_data:
            return False
        
        # 更新已确认的食材
        if "confirmed_ingredients" not in user_data["current_session"]:
            user_data["current_session"]["confirmed_ingredients"] = {}
        
        user_data["current_session"]["confirmed_ingredients"][ingredient] = status
        
        # 更新食材库存
        if "ingredient_inventory" not in user_data:
            user_data["ingredient_inventory"] = {}
        
        if status == "have":
            user_data["ingredient_inventory"][ingredient] = True
        elif status == "dont_have":
            user_data["ingredient_inventory"][ingredient] = False
        
        return self.update_user(user_id, user_data)
    
    def get_confirmed_ingredients(self, user_id: str) -> Dict[str, str]:
        """获取已确认的食材"""
        user_data = self.get_user(user_id)
        if not user_data:
            return {}
        
        return user_data.get("current_session", {}).get("confirmed_ingredients", {})
    
    def is_ingredient_confirmed(self, user_id: str, ingredient: str) -> bool:
        """检查食材是否已确认"""
        confirmed = self.get_confirmed_ingredients(user_id)
        return ingredient in confirmed
    
    def set_current_dish(self, user_id: str, dish: str, taste: str = ""):
        """设置当前做的菜"""
        updates = {
            "current_session": {
                "dish": dish,
                "confirmed_ingredients": {},
                "missing_ingredients": [],
                "cooking_steps": [],
                "current_step": 0
            }
        }
        
        if taste:
            updates["current_session"]["taste"] = taste
        
        return self.update_user(user_id, updates)
    
    def add_cooking_step(self, user_id: str, step: str):
        """添加烹饪步骤"""
        user_data = self.get_user(user_id)
        if not user_data:
            return False
        
        if "cooking_steps" not in user_data["current_session"]:
            user_data["current_session"]["cooking_steps"] = []
        
        user_data["current_session"]["cooking_steps"].append({
            "step": step,
            "timestamp": datetime.now().isoformat(),
            "completed": False
        })
        
        return self.update_user(user_id, user_data)
    
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
            "preferences": user_data["profile"]["preferences"],
            "allergies": user_data["profile"]["allergies"],
            "current_dish": user_data["current_session"]["dish"],
            "confirmed_ingredients": user_data["current_session"]["confirmed_ingredients"],
            "last_active": user_data["last_active"]
        }
    
    def clear_session(self, user_id: str):
        """清除当前会话"""
        updates = {
            "current_session": {
                "dish": "",
                "confirmed_ingredients": {},
                "missing_ingredients": [],
                "cooking_steps": [],
                "current_step": 0
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

# 全局用户管理器实例
user_manager = UserManager()

def get_user_manager() -> UserManager:
    """获取用户管理器实例"""
    return user_manager 