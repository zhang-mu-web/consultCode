#!/usr/bin/env python3
"""
快速查看Redis数据库
"""

import json
import redis
import sys

def quick_view():
    """快速查看数据库内容"""
    try:
        # 连接Redis
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        print("✅ 成功连接到Redis")
    except:
        print("❌ 无法连接到Redis，请确保Redis服务正在运行")
        return
    
    # 获取所有键
    all_keys = r.keys("*")
    if not all_keys:
        print("📭 数据库是空的")
        return
    
    print(f"\n📊 数据库中共有 {len(all_keys)} 个键:")
    
    # 分类统计
    cooking_user_keys = [k for k in all_keys if k.startswith("cooking_user:")]
    user_profile_keys = [k for k in all_keys if k.startswith("user_profile:")]
    conv_keys = [k for k in all_keys if k.startswith("conversation:")]
    other_keys = [k for k in all_keys if not k.startswith(("cooking_user:", "user_profile:", "conversation:"))]
    
    print(f"👨‍🍳 烹饪用户: {len(cooking_user_keys)} 个")
    print(f"👤 用户档案: {len(user_profile_keys)} 个")
    print(f"💬 对话数据: {len(conv_keys)} 个")
    print(f"📝 其他数据: {len(other_keys)} 个")
    
    # 显示所有键
    print(f"\n🔑 所有键:")
    for i, key in enumerate(sorted(all_keys), 1):
        key_type = r.type(key)
        ttl = r.ttl(key)
        ttl_str = f"TTL:{ttl}s" if ttl > 0 else "永久"
        print(f"  {i:2d}. {key} ({key_type}, {ttl_str})")
    
    # 如果有烹饪用户数据，显示详细信息
    if cooking_user_keys:
        print(f"\n👨‍🍳 烹饪用户数据详情:")
        for key in sorted(cooking_user_keys):
            try:
                data = r.get(key)
                if data:
                    user_data = json.loads(data)
                    print(f"\n  📝 {key}:")
                    for k, v in user_data.items():
                        if isinstance(v, dict):
                            print(f"    {k}: {json.dumps(v, ensure_ascii=False)}")
                        else:
                            print(f"    {k}: {v}")
            except:
                print(f"  📝 {key}: 数据格式错误")
    
    # 如果有用户档案数据，显示详细信息
    if user_profile_keys:
        print(f"\n👤 用户档案数据详情:")
        for key in sorted(user_profile_keys):
            try:
                data = r.get(key)
                if data:
                    user_data = json.loads(data)
                    print(f"\n  📝 {key}:")
                    for k, v in user_data.items():
                        if isinstance(v, dict):
                            print(f"    {k}: {json.dumps(v, ensure_ascii=False)}")
                        else:
                            print(f"    {k}: {v}")
            except:
                print(f"  📝 {key}: 数据格式错误")
    
    # 如果有对话数据，显示详细信息
    if conv_keys:
        print(f"\n💬 对话数据详情:")
        for key in sorted(conv_keys):
            try:
                data = r.get(key)
                if data:
                    conv_data = json.loads(data)
                    print(f"\n  💬 {key}:")
                    if isinstance(conv_data, list):
                        print(f"    对话轮数: {len(conv_data)}")
                        for i, msg in enumerate(conv_data[-3:], 1):  # 只显示最后3轮
                            role = msg.get('role', 'unknown')
                            content = msg.get('content', '')[:50]
                            print(f"    {i}. [{role}] {content}...")
                    else:
                        print(f"    数据: {json.dumps(conv_data, ensure_ascii=False)}")
            except:
                print(f"  💬 {key}: 数据格式错误")

if __name__ == '__main__':
    quick_view() 