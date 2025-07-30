#!/usr/bin/env python3
"""
信息提取器
从用户输入中提取关键信息并更新用户属性
"""

import re
import json
from typing import Dict, List, Tuple, Optional
from user_manager import get_user_manager

class InfoExtractor:
    """信息提取器"""
    
    def __init__(self):
        self.user_manager = get_user_manager()
        
        # 食材关键词映射
        self.ingredient_keywords = {
            "五花肉": ["五花肉", "猪肉", "肥瘦相间"],
            "鸡肉": ["鸡肉", "鸡胸肉", "鸡腿肉", "鸡翅"],
            "牛肉": ["牛肉", "牛腩", "牛排"],
            "羊肉": ["羊肉", "羊排"],
            "土豆": ["土豆", "马铃薯"],
            "胡萝卜": ["胡萝卜", "红萝卜"],
            "洋葱": ["洋葱", "葱头"],
            "大蒜": ["大蒜", "蒜", "蒜头"],
            "生姜": ["生姜", "姜", "姜片"],
            "青椒": ["青椒", "辣椒", "甜椒"],
            "盐": ["盐", "食盐"],
            "糖": ["糖", "白砂糖", "白糖"],
            "生抽": ["生抽", "酱油"],
            "老抽": ["老抽", "深色酱油"],
            "料酒": ["料酒", "黄酒"],
            "醋": ["醋", "白醋", "米醋"],
            "辣椒": ["辣椒", "辣椒粉", "辣椒面"],
            "胡椒粉": ["胡椒粉", "黑胡椒", "白胡椒"],
            "八角": ["八角", "大料"],
            "桂皮": ["桂皮", "肉桂"],
            "花椒": ["花椒", "麻椒"],
            "孜然": ["孜然", "孜然粉"],
            "鸡蛋": ["鸡蛋", "蛋"],
            "面粉": ["面粉", "低筋面粉", "高筋面粉", "普通面粉"],
            "油": ["油", "食用油", "植物油", "炒菜油"],
            "牛奶": ["牛奶", "鲜奶"],
            "黄油": ["黄油", "奶油"],
            "淀粉": ["淀粉", "玉米淀粉", "土豆淀粉"],
            "泡打粉": ["泡打粉", "发酵粉"],
            "酵母": ["酵母", "干酵母"]
        }
        
        # 口味关键词
        self.taste_keywords = {
            "sweet": ["甜", "甜口", "甜味", "糖", "蜂蜜"],
            "savory": ["咸", "咸口", "咸味", "盐"],
            "spicy": ["辣", "辣口", "麻辣", "辣椒", "花椒"],
            "sour": ["酸", "酸口", "醋", "柠檬"],
            "umami": ["鲜", "鲜味", "味精", "鸡精"]
        }
        
        # 烹饪水平关键词
        self.cooking_level_keywords = {
            "beginner": ["新手", "初学者", "不会", "第一次", "刚开始", "不太会"],
            "intermediate": ["一般", "还行", "做过几次", "有点经验", "会一点"],
            "advanced": ["熟练", "经常做", "很会做", "专业", "老手"]
        }
        
        # 厨具关键词
        self.equipment_keywords = {
            "炒锅": ["炒锅", "平底锅", "铁锅"],
            "蒸锅": ["蒸锅", "蒸笼"],
            "烤箱": ["烤箱", "烤炉"],
            "微波炉": ["微波炉"],
            "电饭煲": ["电饭煲", "电饭锅"],
            "搅拌机": ["搅拌机", "料理机"],
            "打蛋器": ["打蛋器", "电动打蛋器"],
            "擀面杖": ["擀面杖"],
            "菜刀": ["菜刀", "刀"],
            "砧板": ["砧板", "案板"]
        }
        
        # 过敏原关键词
        self.allergy_keywords = {
            "花生": ["花生", "花生酱", "花生过敏"],
            "海鲜": ["海鲜", "虾", "蟹", "贝类", "海鲜过敏"],
            "鸡蛋": ["鸡蛋过敏", "蛋过敏"],
            "牛奶": ["牛奶过敏", "乳糖不耐"],
            "坚果": ["坚果", "核桃", "杏仁", "坚果过敏"],
            "大豆": ["大豆", "黄豆", "大豆过敏"],
            "小麦": ["小麦", "麸质", "面筋", "小麦过敏"]
        }
    
    def extract_ingredients(self, text: str) -> List[Tuple[str, str]]:
        """提取食材信息"""
        extracted = []
        
        for ingredient, keywords in self.ingredient_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    status = self._determine_ingredient_status(text, keyword)
                    if status:
                        extracted.append((ingredient, status))
                        break
        
        return extracted
    
    def _determine_ingredient_status(self, text: str, ingredient: str) -> Optional[str]:
        """判断食材状态"""
        have_patterns = [
            rf"有{ingredient}",
            rf"{ingredient}有",
            rf"家里有{ingredient}",
            rf"{ingredient}家里有"
        ]
        
        dont_have_patterns = [
            rf"没有{ingredient}",
            rf"{ingredient}没有",
            rf"家里没有{ingredient}",
            rf"{ingredient}家里没有"
        ]
        
        for pattern in have_patterns:
            if re.search(pattern, text):
                return "have"
        
        for pattern in dont_have_patterns:
            if re.search(pattern, text):
                return "dont_have"
        
        if ingredient in text:
            return "have"
        
        return None
    
    def extract_taste_preference(self, text: str) -> List[str]:
        """提取口味偏好"""
        preferences = []
        
        for taste, keywords in self.taste_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    preferences.append(taste)
                    break
        
        return preferences
    
    def extract_cooking_level(self, text: str) -> Optional[str]:
        """提取烹饪水平"""
        for level, keywords in self.cooking_level_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return level
        return None
    
    def extract_equipment(self, text: str) -> List[str]:
        """提取厨具信息"""
        equipment = []
        
        for equip, keywords in self.equipment_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    # 判断是否有/没有
                    status = self._determine_equipment_status(text, keyword)
                    if status == "have":
                        equipment.append(equip)
                    break
        
        return equipment
    
    def _determine_equipment_status(self, text: str, equipment: str) -> Optional[str]:
        """判断厨具状态"""
        # 检查是否有
        have_patterns = [
            rf"有{equipment}",
            rf"{equipment}有",
            rf"家里有{equipment}",
            rf"{equipment}家里有"
        ]
        
        # 检查是否没有
        dont_have_patterns = [
            rf"没有{equipment}",
            rf"{equipment}没有",
            rf"家里没有{equipment}",
            rf"{equipment}家里没有"
        ]
        
        # 检查是否有
        for pattern in have_patterns:
            if re.search(pattern, text):
                return "have"
        
        # 检查是否没有
        for pattern in dont_have_patterns:
            if re.search(pattern, text):
                return "dont_have"
        
        return None
    
    def extract_allergies(self, text: str) -> List[str]:
        """提取过敏信息"""
        allergies = []
        
        for allergy, keywords in self.allergy_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    allergies.append(allergy)
                    break
        
        return allergies
    
    def extract_family_size(self, text: str) -> Optional[int]:
        """提取用餐人数"""
        # 匹配数字+人
        pattern = r"(\d+)个人?|(\d+)人|(\d+)口人"
        match = re.search(pattern, text)
        if match:
            for group in match.groups():
                if group:
                    return int(group)
        
        # 匹配具体描述
        size_keywords = {
            1: ["一个人", "自己", "单身"],
            2: ["两个人", "夫妻", "情侣"],
            3: ["三个人", "三口之家"],
            4: ["四个人", "四口之家"],
            5: ["五个人", "五口之家"]
        }
        
        for size, keywords in size_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return size
        
        return None
    
    def extract_dish_info(self, text: str) -> Dict:
        """提取菜品信息"""
        dish_info = {
            "dish": "",
            "taste": ""
        }
        
        dish_keywords = {
            "红烧肉": ["红烧肉", "红烧"],
            "糖醋里脊": ["糖醋里脊", "糖醋"],
            "宫保鸡丁": ["宫保鸡丁", "宫保"],
            "麻婆豆腐": ["麻婆豆腐", "麻婆"],
            "番茄炒蛋": ["番茄炒蛋", "西红柿炒蛋"],
            "青椒炒肉": ["青椒炒肉", "青椒肉丝"],
            "土豆炖牛肉": ["土豆炖牛肉", "土豆牛肉"],
            "水煮鱼": ["水煮鱼", "水煮"],
            "回锅肉": ["回锅肉", "回锅"],
            "鱼香肉丝": ["鱼香肉丝", "鱼香"],
            "巧克力蛋糕": ["巧克力蛋糕", "巧克力"],
            "饼干": ["饼干", "曲奇"],
            "面包": ["面包"],
            "饺子": ["饺子"],
            "面条": ["面条", "面"],
            "米饭": ["米饭", "白米饭"]
        }
        
        for dish, keywords in dish_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    dish_info["dish"] = dish
                    break
            if dish_info["dish"]:
                break
        
        tastes = self.extract_taste_preference(text)
        if tastes:
            dish_info["taste"] = tastes[0]
        
        return dish_info
    
    def extract_all_info(self, text: str, user_id: str) -> Dict:
        """提取所有信息并更新用户属性"""
        extracted_info = {
            "ingredients": [],
            "taste_preferences": [],
            "cooking_level": None,
            "equipment": [],
            "dish_info": {},
            "allergies": [],
            "family_size": None
        }
        
        # 提取各种信息
        extracted_info["ingredients"] = self.extract_ingredients(text)
        extracted_info["taste_preferences"] = self.extract_taste_preference(text)
        extracted_info["cooking_level"] = self.extract_cooking_level(text)
        extracted_info["equipment"] = self.extract_equipment(text)
        extracted_info["dish_info"] = self.extract_dish_info(text)
        extracted_info["allergies"] = self.extract_allergies(text)
        extracted_info["family_size"] = self.extract_family_size(text)
        
        # 更新用户属性
        self._update_user_from_extracted_info(user_id, extracted_info)
        
        return extracted_info
    
    def _update_user_from_extracted_info(self, user_id: str, extracted_info: Dict):
        """根据提取的信息更新用户属性"""
        # 更新食材状态
        for ingredient, status in extracted_info["ingredients"]:
            self.user_manager.update_ingredient_status(user_id, ingredient, status)
        
        # 更新口味偏好
        if extracted_info["taste_preferences"]:
            self.user_manager.update_preferences(user_id, "taste", extracted_info["taste_preferences"])
        
        # 更新烹饪水平
        if extracted_info["cooking_level"]:
            self.user_manager.update_cooking_level(user_id, extracted_info["cooking_level"])
        
        # 更新厨具信息
        if extracted_info["equipment"]:
            self.user_manager.update_user(user_id, {
                "profile": {
                    "kitchen_equipment": extracted_info["equipment"]
                }
            })
        
        # 更新当前菜品
        if extracted_info["dish_info"]["dish"]:
            taste = extracted_info["dish_info"]["taste"]
            self.user_manager.set_current_dish(user_id, extracted_info["dish_info"]["dish"], taste)
        
        # 更新过敏信息
        for allergy in extracted_info["allergies"]:
            self.user_manager.add_allergy(user_id, allergy)
        
        # 更新用餐人数
        if extracted_info["family_size"]:
            self.user_manager.update_user(user_id, {
                "profile": {
                    "family_size": extracted_info["family_size"]
                }
            })
    
    def get_user_context_for_prompt(self, user_id: str) -> Dict:
        """获取用户上下文信息用于prompt"""
        user_data = self.user_manager.get_user(user_id)
        if not user_data:
            return {}
        
        return {
            "cooking_level": user_data["profile"]["cooking_level"],
            "taste_preferences": user_data["profile"]["preferences"]["taste"],
            "allergies": user_data["profile"]["allergies"],
            "kitchen_equipment": user_data["profile"]["kitchen_equipment"],
            "family_size": user_data["profile"]["family_size"],
            "current_dish": user_data["current_session"]["dish"],
            "confirmed_ingredients": user_data["current_session"]["confirmed_ingredients"],
            "ingredient_inventory": user_data["ingredient_inventory"]
        }

# 全局信息提取器实例
info_extractor = InfoExtractor()

def get_info_extractor() -> InfoExtractor:
    """获取信息提取器实例"""
    return info_extractor 