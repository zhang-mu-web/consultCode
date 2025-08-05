#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS集成测试文件
测试烹饪咨询系统的TTS功能
"""

import asyncio
import threading
import time
from tts.tts_downlink_manager import TTSDownlinkManager, TTSFlowMode

# 创建TTS管理器实例
tts_manager = TTSDownlinkManager(tts_endpoint='192.168.2.109:50051', downlink_endpoint='192.168.2.88:50055')

async def async_tts_speak_v2(text, language, user_id):
    """异步TTS播报函数"""
    try:
        print(f"🎤 开始TTS播报: {text[:50]}...")
        await tts_manager.setup_connections()
        await tts_manager.process_tts_request(
            text=text,
            user_id=user_id,
            mode=TTSFlowMode.STREAMING,
            voice_id="1",
            language=language
        )
        print(f"✅ TTS播报完成")
    except Exception as e:
        print(f"❌ TTS处理异常: {e}")
    finally:
        await tts_manager.close_connections()

def tts_push_callback(event, content, language_id, msg, user_id=None):
    """TTS播报回调函数"""
    print(f"[TTS播报] event={event}, content={content}, lang={language_id}, msg={msg}")
    if msg:
        if user_id is None:
            user_id = "default"
        def run():
            try:
                # 创建新的事件循环，避免阻塞主线程
                new_loop = asyncio.new_event_loop()
                # 设置新的事件循环
                asyncio.set_event_loop(new_loop)
                # 运行异步任务
                new_loop.run_until_complete(async_tts_speak_v2(msg, language_id, user_id))
            except Exception as e:
                print(f"❌ TTS播报异常: {e}")
            finally:
                # 确保事件循环正确关闭
                try:
                    if not new_loop.is_closed():
                        new_loop.close()
                except Exception as e:
                    print(f"❌ 关闭事件循环异常: {e}")
        # 启动新线程并执行异步任务
        threading.Thread(target=run, daemon=True).start()

def test_tts_integration():
    """测试TTS集成功能"""
    print("🧪 开始测试TTS集成功能")
    
    # 测试用例
    test_cases = [
        {
            "event": "cooking_advice",
            "content": "用户询问如何做红烧肉",
            "language_id": "zh",
            "msg": "好的，我来教您做红烧肉。首先需要准备五花肉、生抽、老抽、料酒等食材。",
            "user_id": "test_user_001"
        },
        {
            "event": "cooking_advice", 
            "content": "用户询问如何做糖醋里脊",
            "language_id": "zh",
            "msg": "糖醋里脊的做法很简单，需要里脊肉、淀粉、糖、醋等调料。",
            "user_id": "test_user_002"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 测试用例 {i}:")
        print(f"   事件: {test_case['event']}")
        print(f"   内容: {test_case['content']}")
        print(f"   语言: {test_case['language_id']}")
        print(f"   消息: {test_case['msg']}")
        print(f"   用户ID: {test_case['user_id']}")
        
        # 调用TTS播报
        tts_push_callback(
            test_case['event'],
            test_case['content'], 
            test_case['language_id'],
            test_case['msg'],
            test_case['user_id']
        )
        
        # 等待一段时间让TTS处理完成
        time.sleep(3)
    
    print("\n✅ TTS集成测试完成")

if __name__ == "__main__":
    test_tts_integration() 