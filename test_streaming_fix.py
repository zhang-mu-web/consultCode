#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修正后的流式处理逻辑
验证结束帧是否在音频播放完成后发送
"""

import asyncio
import logging
from tts.tts_downlink_manager import TTSDownlinkManager, TTSFlowMode

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_streaming_fix():
    """测试修正后的流式处理"""
    print("🧪 开始测试修正后的流式处理")
    
    # 创建TTS管理器
    tts_manager = TTSDownlinkManager(tts_endpoint='192.168.2.109:50051', downlink_endpoint='192.168.2.88:50055')
    
    try:
        await tts_manager.setup_connections()
        
        # 测试用例
        test_cases = [
            {
                "text": "你好，这是一个流式处理测试。",
                "user_id": "stream_test_001",
                "description": "短文本测试"
            },
            {
                "text": "这是一个较长的测试文本，用来验证流式处理是否正常工作，确保音频播放完成后再发送结束帧。",
                "user_id": "stream_test_002",
                "description": "长文本测试"
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 测试用例 {i}: {test_case['description']}")
            print(f"   文本: {test_case['text']}")
            print(f"   用户ID: {test_case['user_id']}")
            
            # 调用流式TTS处理
            success = await tts_manager.process_tts_request(
                text=test_case['text'],
                user_id=test_case['user_id'],
                mode=TTSFlowMode.STREAMING,
                voice_id="1",
                language="zh"
            )
            
            if success:
                print(f"   ✅ {test_case['description']} 测试成功")
            else:
                print(f"   ❌ {test_case['description']} 测试失败")
            
            # 等待一段时间再进行下一个测试
            await asyncio.sleep(2)
        
        print(f"\n🎉 所有测试用例完成！")
        print(f"📊 请检查日志中的时间戳，确认结束帧在音频播放完成后发送")
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
    finally:
        await tts_manager.close_connections()

def main():
    """主函数"""
    print("🔧 开始测试修正后的流式处理")
    print("=" * 60)
    print("📋 测试目标:")
    print("1. 验证流式处理逻辑是否正确")
    print("2. 确认结束帧在音频播放完成后发送")
    print("3. 检查音频播放时间估算是否合理")
    print("4. 验证异常处理机制")
    print("=" * 60)
    
    asyncio.run(test_streaming_fix())
    
    print("\n" + "=" * 60)
    print("📋 验证要点:")
    print("1. 查看日志中的'⏳ 等待音频播放完成'信息")
    print("2. 确认等待时间是否合理（基于音频块数量计算）")
    print("3. 检查'🎯 发送结束帧'的时间戳是否在等待之后")
    print("4. 验证音频播放是否流畅，没有提前中断")

if __name__ == "__main__":
    main() 