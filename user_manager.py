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
        """从文本中智能提取菜品名称"""
        import re
        
        # 清理文本
        text = text.strip()
        if not text:
            return ""
        
        # 1. 智能模式匹配 - 使用更灵活的匹配模式
        smart_patterns = [
            # 直接表达想做某菜
            r"我想做(.+?)(?:吗|呢|啊|？|\?|$|，|。|！)",
            r"我要做(.+?)(?:吗|呢|啊|？|\?|$|，|。|！)",
            r"准备做(.+?)(?:吗|呢|啊|？|\?|$|，|。|！)",
            r"打算做(.+?)(?:吗|呢|啊|？|\?|$|，|。|！)",
            
            # 询问做法
            r"(.+?)怎么做",
            r"如何做(.+?)",
            r"(.+?)的做法",
            r"(.+?)怎么做好吃",
            r"(.+?)的烹饪方法",
            r"(.+?)有哪些做法",
            
            # 其他表达方式
            r"做(.+?)(?:吗|呢|啊|？|\?|$|，|。|！)",
            r"学(.+?)(?:吗|呢|啊|？|\?|$|，|。|！)",
            r"教我做(.+?)(?:吗|呢|啊|？|\?|$|，|。|！)",
            r"帮我做(.+?)(?:吗|呢|啊|？|\?|$|，|。|！)",
        ]
        
        for pattern in smart_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                candidate = match.strip()
                if self._is_valid_dish_name(candidate):
                    return candidate
        
        # 2. 关键词智能提取
        dish_candidates = self._extract_dish_candidates(text)
        if dish_candidates:
            # 返回最可能的菜品名称
            return dish_candidates[0]
        
        # 3. 分词分析
        return self._analyze_text_with_jieba(text)
    
    def _is_valid_dish_name(self, candidate: str) -> bool:
        """判断是否为有效的菜品名称"""
        if not candidate or len(candidate) < 2:
            return False
        
        # 过滤掉明显不是菜品的词
        invalid_words = [
            '什么', '怎么', '如何', '哪些', '做法', '方法', '烹饪', '料理',
            '菜', '饭', '汤', '面', '饼', '包', '饺', '糕', '点', '食',
            '好吃', '美味', '香', '甜', '咸', '辣', '酸', '苦',
            '今天', '明天', '昨天', '现在', '马上', '立刻', '现在',
            '可以', '能够', '应该', '需要', '想要', '希望', '喜欢',
            '这个', '那个', '这些', '那些', '什么', '哪个', '哪些'
        ]
        
        # 检查是否包含无效词
        for invalid_word in invalid_words:
            if invalid_word in candidate:
                return False
        
        # 检查长度和字符
        if len(candidate) > 20:  # 菜品名称通常不会太长
            return False
        
        # 检查是否包含过多数字或特殊字符
        digit_count = sum(1 for c in candidate if c.isdigit())
        if digit_count > len(candidate) * 0.3:  # 数字占比不能超过30%
            return False
        
        return True
    
    def _extract_dish_candidates(self, text: str) -> list:
        """智能提取菜品候选词"""
        import re
        candidates = []
        
        # 菜品关键词库（按优先级排序）
        dish_keywords = {
            # 炒饭类（优先匹配完整菜品名）
            '炒饭类': ['蛋炒饭', '扬州炒饭', '虾仁炒饭', '火腿炒饭', '鸡肉炒饭', '牛肉炒饭', '什锦炒饭', '菠萝炒饭', '咖喱炒饭'],
            
            # 肉类菜品
            '肉类': ['红烧肉', '糖醋里脊', '宫保鸡丁', '麻婆豆腐', '鱼香肉丝', '回锅肉', '水煮鱼', '酸菜鱼', '清蒸鱼', '红烧鱼', '糖醋鱼', '炸鸡', '烤鸭', '白切鸡', '口水鸡', '辣子鸡', '黄焖鸡', '大盘鸡'],
            '肉': ['肉', '猪肉', '牛肉', '羊肉', '鸡肉', '鸭肉', '鱼肉', '虾肉', '蟹肉'],
            
            # 蔬菜菜品
            '蔬菜': ['青椒炒肉', '蒜蓉青菜', '麻婆豆腐', '地三鲜', '鱼香茄子', '干煸豆角', '醋溜白菜', '蒜蓉菠菜', '清炒小白菜', '干煸四季豆'],
            '蔬菜': ['青菜', '白菜', '菠菜', '韭菜', '芹菜', '香菜', '生菜', '油麦菜', '空心菜', '苋菜'],
            
            # 主食
            '主食': ['米饭', '面条', '饺子', '包子', '馒头', '饼', '面包', '蛋糕', '粥', '汤'],
            
            # 汤类
            '汤类': ['紫菜蛋花汤', '西红柿蛋汤', '冬瓜排骨汤', '玉米排骨汤', '萝卜排骨汤', '鸡汤', '鱼汤', '牛肉汤', '羊肉汤'],
            
            # 特色菜品
            '特色': ['狮子头', '东坡肉', '佛跳墙', '叫花鸡', '北京烤鸭', '麻婆豆腐', '宫保鸡丁', '鱼香肉丝', '回锅肉', '水煮鱼', '酸菜鱼', '清蒸鱼', '红烧鱼', '糖醋鱼', '炸鸡', '烤鸭', '白切鸡', '口水鸡', '辣子鸡', '黄焖鸡', '大盘鸡']
        }
        
        # 按优先级搜索（炒饭类优先）
        for category, keywords in dish_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    # 尝试提取包含关键词的完整菜品名称
                    words = text.split()
                    for word in words:
                        if keyword in word and self._is_valid_dish_name(word):
                            if word not in candidates:
                                candidates.append(word)
        
        # 如果没有找到完整菜品名，尝试提取单个关键词
        if not candidates:
            for category, keywords in dish_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        # 检查关键词前后是否有修饰词
                        pattern = rf'(\w*{keyword}\w*)'
                        matches = re.findall(pattern, text)
                        for match in matches:
                            if self._is_valid_dish_name(match) and match not in candidates:
                                candidates.append(match)
        
        return candidates
    
    def _analyze_text_with_jieba(self, text: str) -> str:
        """使用jieba分词分析文本"""
        try:
            import jieba
            # 使用jieba进行分词
            words = list(jieba.cut(text))
            
            # 菜品相关的词性组合
            dish_patterns = [
                # 形容词 + 名词
                ['红烧', '糖醋', '清蒸', '油炸', '烤', '煮', '炒', '炖', '焖', '煎', '炸'],
                ['肉', '鱼', '鸡', '鸭', '虾', '蟹', '蛋', '豆腐', '青菜', '白菜', '土豆', '茄子', '青椒', '西红柿', '黄瓜', '胡萝卜', '洋葱', '蒜', '姜', '葱', '米饭', '面条', '饺子', '包子', '馒头', '饼', '汤']
            ]
            
            # 查找可能的菜品组合
            for i, word in enumerate(words):
                if i < len(words) - 1:
                    next_word = words[i + 1]
                    # 检查是否是烹饪方法 + 食材的组合
                    if word in dish_patterns[0] and next_word in dish_patterns[1]:
                        candidate = word + next_word
                        if self._is_valid_dish_name(candidate):
                            return candidate
            
            # 如果没有找到组合，尝试单个词
            for word in words:
                if word in dish_patterns[1] and self._is_valid_dish_name(word):
                    return word
                    
        except ImportError:
            # 如果没有jieba，使用简单的分词
            pass
        
        return ""

    def smart_extract_dish(self, text: str, conversation_history: list = None) -> str:
        """智能菜品识别 - 结合上下文和语义理解"""
        import re
        
        # 1. 首先尝试直接提取
        direct_result = self.extract_dish_from_text(text)
        if direct_result:
            return direct_result
        
        # 2. 如果有对话历史，尝试从上下文中识别
        if conversation_history:
            context_result = self._extract_from_context(text, conversation_history)
            if context_result:
                return context_result
        
        # 3. 尝试语义理解
        semantic_result = self._semantic_dish_recognition(text)
        if semantic_result:
            return semantic_result
        
        return ""
    
    def _extract_from_context(self, current_text: str, conversation_history: list) -> str:
        """从对话上下文中提取菜品名称"""
        # 分析对话历史，寻找菜品相关的信息
        dish_mentions = []
        
        for item in conversation_history:
            if item.get('role') == 'user':
                content = item.get('content', '')
                # 提取可能的菜品名称
                extracted = self.extract_dish_from_text(content)
                if extracted:
                    dish_mentions.append(extracted)
        
        # 如果历史中有菜品提及，优先使用
        if dish_mentions:
            # 返回最近提到的菜品
            return dish_mentions[-1]
        
        # 分析当前文本与历史的关系
        current_lower = current_text.lower()
        
        # 检查是否是询问做法的变体
        cooking_questions = ['怎么做', '如何做', '做法', '烹饪', '料理', '步骤', '方法']
        if any(q in current_lower for q in cooking_questions):
            # 从历史中寻找可能的菜品
            for item in reversed(conversation_history):
                if item.get('role') == 'user':
                    content = item.get('content', '')
                    # 寻找包含食材或菜品关键词的内容
                    if any(keyword in content for keyword in ['肉', '鱼', '鸡', '鸭', '虾', '蟹', '蛋', '豆腐', '青菜', '米饭', '面条']):
                        extracted = self.extract_dish_from_text(content)
                        if extracted:
                            return extracted
        
        return ""
    
    def _semantic_dish_recognition(self, text: str) -> str:
        """基于语义理解的菜品识别"""
        import re
        
        # 语义关键词映射
        semantic_keywords = {
            # 炒饭类（优先）
            '蛋炒饭': ['蛋炒饭'],
            '扬州炒饭': ['扬州炒饭'],
            '虾仁炒饭': ['虾仁炒饭'],
            '火腿炒饭': ['火腿炒饭'],
            '鸡肉炒饭': ['鸡肉炒饭'],
            '牛肉炒饭': ['牛肉炒饭'],
            '什锦炒饭': ['什锦炒饭'],
            '菠萝炒饭': ['菠萝炒饭'],
            '咖喱炒饭': ['咖喱炒饭'],
            
            # 肉类相关
            '肉': ['肉', '猪肉', '牛肉', '羊肉', '鸡肉', '鸭肉', '鱼肉', '虾肉', '蟹肉'],
            '红烧': ['红烧肉', '红烧鱼', '红烧鸡', '红烧鸭'],
            '糖醋': ['糖醋里脊', '糖醋鱼', '糖醋排骨'],
            '宫保': ['宫保鸡丁', '宫保肉丁'],
            '鱼香': ['鱼香肉丝', '鱼香茄子'],
            '麻婆': ['麻婆豆腐'],
            '回锅': ['回锅肉'],
            '水煮': ['水煮鱼', '水煮肉片'],
            '酸菜': ['酸菜鱼'],
            '清蒸': ['清蒸鱼', '清蒸鸡'],
            '炸': ['炸鸡', '炸鱼'],
            '烤': ['烤鸭', '烤鸡'],
            '白切': ['白切鸡'],
            '口水': ['口水鸡'],
            '辣子': ['辣子鸡'],
            '黄焖': ['黄焖鸡'],
            '大盘': ['大盘鸡'],
            
            # 蔬菜相关
            '青椒': ['青椒炒肉', '青椒炒蛋'],
            '蒜蓉': ['蒜蓉青菜', '蒜蓉菠菜'],
            '地三鲜': ['地三鲜'],
            '鱼香茄子': ['鱼香茄子'],
            '干煸': ['干煸豆角', '干煸四季豆'],
            '醋溜': ['醋溜白菜'],
            '清炒': ['清炒小白菜'],
            
            # 主食相关
            '米饭': ['米饭', '蛋炒饭', '扬州炒饭'],
            '面条': ['面条', '炸酱面', '阳春面'],
            '饺子': ['饺子', '水饺', '蒸饺'],
            '包子': ['包子', '肉包', '菜包'],
            '馒头': ['馒头', '花卷'],
            '饼': ['饼', '煎饼', '烙饼'],
            '面包': ['面包', '吐司'],
            '蛋糕': ['蛋糕', '生日蛋糕'],
            
            # 汤类
            '紫菜蛋花汤': ['紫菜蛋花汤'],
            '西红柿蛋汤': ['西红柿蛋汤'],
            '排骨汤': ['冬瓜排骨汤', '玉米排骨汤', '萝卜排骨汤'],
            '鸡汤': ['鸡汤'],
            '鱼汤': ['鱼汤'],
            '牛肉汤': ['牛肉汤'],
            '羊肉汤': ['羊肉汤'],
            
            # 特色菜品
            '狮子头': ['狮子头'],
            '东坡肉': ['东坡肉'],
            '佛跳墙': ['佛跳墙'],
            '叫花鸡': ['叫花鸡'],
            '北京烤鸭': ['北京烤鸭']
        }
        
        # 分析文本中的语义关键词
        text_lower = text.lower()
        matched_dishes = []
        
        for keyword, dishes in semantic_keywords.items():
            if keyword in text_lower:
                # 找到匹配的菜品
                for dish in dishes:
                    if dish not in matched_dishes:
                        matched_dishes.append(dish)
        
        # 如果有多个匹配，选择最相关的
        if matched_dishes:
            # 优先选择与文本最匹配的菜品
            for dish in matched_dishes:
                if dish in text:
                    return dish
            # 如果没有完全匹配，返回第一个
            return matched_dishes[0]
        
        # 尝试从文本中提取食材组合
        ingredients = self._extract_ingredients(text)
        if ingredients:
            # 根据食材组合推测菜品
            dish = self._infer_dish_from_ingredients(ingredients)
            if dish:
                return dish
        
        return ""
    
    def _extract_ingredients(self, text: str) -> list:
        """提取文本中的食材"""
        ingredients = []
        
        # 常见食材列表
        common_ingredients = [
            '肉', '猪肉', '牛肉', '羊肉', '鸡肉', '鸭肉', '鱼肉', '虾', '蟹', '蛋', '豆腐',
            '青菜', '白菜', '菠菜', '韭菜', '芹菜', '香菜', '生菜', '油麦菜', '空心菜', '苋菜',
            '土豆', '茄子', '青椒', '西红柿', '黄瓜', '胡萝卜', '洋葱', '蒜', '姜', '葱',
            '米饭', '面条', '饺子', '包子', '馒头', '饼', '面包', '蛋糕', '粥', '汤'
        ]
        
        for ingredient in common_ingredients:
            if ingredient in text:
                ingredients.append(ingredient)
        
        return ingredients
    
    def _infer_dish_from_ingredients(self, ingredients: list) -> str:
        """根据食材组合推测菜品"""
        # 食材组合到菜品的映射
        ingredient_to_dish = {
            # 炒饭类组合（优先）
            ('蛋', '米饭'): '蛋炒饭',
            ('米饭', '蛋'): '蛋炒饭',
            ('虾', '米饭'): '虾仁炒饭',
            ('米饭', '虾'): '虾仁炒饭',
            ('火腿', '米饭'): '火腿炒饭',
            ('米饭', '火腿'): '火腿炒饭',
            ('鸡肉', '米饭'): '鸡肉炒饭',
            ('米饭', '鸡肉'): '鸡肉炒饭',
            ('牛肉', '米饭'): '牛肉炒饭',
            ('米饭', '牛肉'): '牛肉炒饭',
            
            # 其他菜品组合
            ('肉',): '红烧肉',
            ('鱼',): '清蒸鱼',
            ('鸡',): '白切鸡',
            ('鸭',): '烤鸭',
            ('虾',): '白灼虾',
            ('蛋',): '炒蛋',
            ('豆腐',): '麻婆豆腐',
            ('青菜',): '清炒青菜',
            ('白菜',): '醋溜白菜',
            ('青椒', '肉'): '青椒炒肉',
            ('青椒', '蛋'): '青椒炒蛋',
            ('西红柿', '蛋'): '西红柿炒蛋',
            ('土豆', '肉'): '土豆炖肉',
            ('茄子',): '鱼香茄子',
            ('米饭',): '米饭',
            ('面条',): '面条',
            ('饺子',): '饺子',
            ('包子',): '包子',
            ('馒头',): '馒头',
            ('面包',): '面包',
        }
        
        # 将食材列表转换为元组以便查找
        ingredients_tuple = tuple(sorted(ingredients))
        
        # 直接匹配
        if ingredients_tuple in ingredient_to_dish:
            return ingredient_to_dish[ingredients_tuple]
        
        # 部分匹配（如果食材列表是某个组合的子集）
        for ingredient_combo, dish in ingredient_to_dish.items():
            if all(ingredient in ingredients for ingredient in ingredient_combo):
                return dish
        
        # 如果没有匹配，返回第一个食材作为菜品名
        if ingredients:
            return ingredients[0]
        
        return ""

    def smart_complete_dish(self, user_id: str, conversation_history: list = None, user_query: str = "") -> bool:
        """智能完成菜品 - 根据对话进度和用户行为判断是否完成"""
        user_data = self.get_user(user_id)
        if not user_data:
            return False
        
        current_dish = user_data.get('current_session', {}).get('dish', '')
        if not current_dish:
            return False
        
        # 确保learned_dishes字段存在
        if "learned_dishes" not in user_data:
            user_data["learned_dishes"] = []
        
        # 检查是否已经学会了这道菜
        if current_dish in user_data["learned_dishes"]:
            return True  # 已经学会了，不需要重复添加
        
        # 智能判断完成条件
        completion_score = 0
        
        # 1. 检查对话历史长度（基础分数）
        if conversation_history:
            if len(conversation_history) >= 8:
                completion_score += 2  # 对话较长，说明进行了详细指导
            elif len(conversation_history) >= 5:
                completion_score += 1  # 对话中等长度
        
        # 2. 检查用户查询中的完成关键词
        if user_query:
            completion_keywords = [
                '完成', '好了', '做完了', '成功了', '味道不错', '很好吃', '满意', '谢谢',
                '接下来', '然后呢', '下一步', '继续', '还有吗', '然后做什么',
                '完成了吗', '做好了吗', '可以了吗', '结束了吗'
            ]
            user_query_lower = user_query.lower()
            for keyword in completion_keywords:
                if keyword in user_query_lower:
                    completion_score += 3  # 用户明确表达完成或继续的意图
                    break
        
        # 3. 检查是否经过了主要步骤（通过对话内容判断）
        if conversation_history:
            step_keywords = ['食材', '准备', '切', '炒', '煮', '蒸', '煎', '炸', '调味', '装盘']
            conversation_text = ' '.join([item.get('content', '') for item in conversation_history])
            conversation_lower = conversation_text.lower()
            
            step_count = sum(1 for keyword in step_keywords if keyword in conversation_lower)
            if step_count >= 3:
                completion_score += 2  # 包含了多个烹饪步骤
            elif step_count >= 1:
                completion_score += 1  # 至少包含一个烹饪步骤
        
        # 4. 检查用户是否询问过具体步骤
        if conversation_history:
            step_questions = ['怎么', '如何', '步骤', '方法', '时间', '火候', '温度']
            for item in conversation_history:
                if item.get('role') == 'user':
                    content = item.get('content', '').lower()
                    if any(question in content for question in step_questions):
                        completion_score += 1  # 用户询问过具体步骤
                        break
        
        # 判断是否完成（总分达到5分即可认为完成）
        if completion_score >= 5:
            # 将菜品添加到已学会列表
            if current_dish not in user_data["learned_dishes"]:
                user_data["learned_dishes"].append(current_dish)
            
            # 清空当前菜品
            user_data["current_session"]["dish"] = ""
            
            # 更新最后活跃时间
            user_data["last_active"] = datetime.now().isoformat()
            
            # 保存到Redis
            key = f"{self.user_prefix}{user_id}"
            self.redis_client.set(key, json.dumps(user_data, ensure_ascii=False))
            
            print(f"用户 {user_id} 智能完成菜品: {current_dish} (完成分数: {completion_score})")
            return True
        
        return False

# 全局用户管理器实例
user_manager = UserManager()

def get_user_manager() -> UserManager:
    """获取用户管理器实例"""
    return user_manager 