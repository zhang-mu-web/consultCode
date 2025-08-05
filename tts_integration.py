#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TTS和Downlink服务集成管理器
为烹饪咨询系统提供语音合成和音频播放功能
"""

import os
import sys
import asyncio
import time
import json
import logging
import uuid
from typing import List, Optional, Callable
from enum import Enum

# 添加tts目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tts'))

import grpc
from tts import tts_service_pb2, tts_service_pb2_grpc
from tts import downlink_pb2
from tts import downlink_pb2_grpc as downlink_grpc

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TTSMode(Enum):
    """TTS模式"""
    SIMPLE = "simple"           # 简单模式：直接合成并播放
    STREAMING = "streaming"     # 流式模式：实时合成和播放

class CookingTTSManager:
    """烹饪咨询TTS管理器"""
    
    def __init__(self, 
                 tts_endpoint='192.168.2.109:50051', 
                 downlink_endpoint='192.168.2.88:50055',
                 user_id=None,
                 device_id=None):
        self.tts_endpoint = tts_endpoint
        self.downlink_endpoint = downlink_endpoint
        
        # 用户和设备ID
        self.user_id = user_id or "cooking_user_001"
        self.device_id = device_id or "cooking_device_001"
        
        # gRPC连接
        self.tts_channel = None
        self.tts_stub = None
        self.downlink_channel = None
        self.downlink_stub = None
        
        # 音频参数
        self.sample_rate = 16000
        self.channels = 1
        self.bit_depth = 16
        
        # 语音参数
        self.voice_id = "1"  # 默认语音ID
        self.language = "zh"  # 中文
        
        # 状态管理
        self.is_connected = False
        self.current_task_id = None
        
        # 统计信息
        self.stats = {
            'tts_calls': 0,
            'audio_chunks_sent': 0,
            'total_pcm_bytes': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def connect(self):
        """建立gRPC连接"""
        try:
            # 连接TTS服务
            self.tts_channel = grpc.aio.insecure_channel(self.tts_endpoint)
            self.tts_stub = tts_service_pb2_grpc.TTSServiceStub(self.tts_channel)
            
            # 连接downlink服务
            self.downlink_channel = grpc.aio.insecure_channel(self.downlink_endpoint)
            self.downlink_stub = downlink_grpc.DownlinkServiceStub(self.downlink_channel)
            
            # 健康检查
            await self._health_check()
            
            self.is_connected = True
            logger.info(f"✅ TTS和Downlink服务连接成功")
            logger.info(f"   TTS服务: {self.tts_endpoint}")
            logger.info(f"   Downlink服务: {self.downlink_endpoint}")
            logger.info(f"   用户ID: {self.user_id}")
            logger.info(f"   设备ID: {self.device_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 连接失败: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """断开gRPC连接"""
        try:
            if self.tts_channel:
                await self.tts_channel.close()
            if self.downlink_channel:
                await self.downlink_channel.close()
            
            self.is_connected = False
            logger.info("✅ 连接已断开")
            
        except Exception as e:
            logger.error(f"❌ 断开连接失败: {e}")
    
    async def _health_check(self):
        """健康检查"""
        try:
            # TTS服务健康检查
            tts_request = tts_service_pb2.HealthCheckRequest(service="tts")
            tts_response = await self.tts_stub.HealthCheck(tts_request)
            logger.info(f"TTS服务状态: {tts_response.status}")
            
            # Downlink服务健康检查
            downlink_request = downlink_pb2.HealthCheckRequest(client_id="cooking_client")
            downlink_response = await self.downlink_stub.HealthCheck(downlink_request)
            logger.info(f"Downlink服务状态: {'健康' if downlink_response.healthy else '不健康'}")
            
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            raise
    
    async def speak_text(self, text: str, mode: TTSMode = TTSMode.SIMPLE):
        """将文本转换为语音并播放"""
        if not self.is_connected:
            logger.error("❌ 服务未连接")
            return False
        
        try:
            self.stats['start_time'] = time.time()
            self.stats['tts_calls'] += 1
            
            logger.info(f"🎤 开始语音合成: {text[:50]}...")
            
            if mode == TTSMode.SIMPLE:
                success = await self._simple_tts(text)
            elif mode == TTSMode.STREAMING:
                success = await self._streaming_tts(text)
            else:
                logger.error(f"❌ 不支持的TTS模式: {mode}")
                return False
            
            self.stats['end_time'] = time.time()
            
            if success:
                duration = self.stats['end_time'] - self.stats['start_time']
                logger.info(f"✅ 语音播放完成 (耗时: {duration:.2f}秒)")
            else:
                logger.error("❌ 语音播放失败")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 语音合成失败: {e}")
            return False
    
    async def _simple_tts(self, text: str) -> bool:
        """简单TTS模式"""
        try:
            # 生成任务ID
            task_id = f"cooking_tts_{uuid.uuid4().hex[:8]}"
            self.current_task_id = task_id
            
            # 调用TTS服务
            audio_chunks = await self._call_tts_service(text)
            
            if not audio_chunks:
                logger.error("❌ TTS服务未返回音频数据")
                return False
            
            # 发送音频到downlink服务
            success = await self._send_audio_to_downlink(audio_chunks, task_id)
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 简单TTS失败: {e}")
            return False
    
    async def _streaming_tts(self, text: str) -> bool:
        """流式TTS模式"""
        try:
            # 生成任务ID和会话ID
            task_id = f"cooking_stream_{uuid.uuid4().hex[:8]}"
            stream_session_id = f"session_{uuid.uuid4().hex[:8]}"
            self.current_task_id = task_id
            
            logger.info(f"🔄 开始流式TTS处理")
            
            # 流式调用TTS服务
            audio_chunks = await self._call_tts_service_streaming(text)
            
            if not audio_chunks:
                logger.error("❌ 流式TTS服务未返回音频数据")
                return False
            
            # 流式发送音频到downlink服务
            success = await self._send_audio_stream_to_downlink(audio_chunks, task_id, stream_session_id)
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 流式TTS失败: {e}")
            return False
    
    async def _call_tts_service(self, text: str) -> List[bytes]:
        """调用TTS服务"""
        try:
            # 生成UUID
            uuid_str = f"cooking_{uuid.uuid4().hex[:8]}"
            
            # 创建TTS请求
            tts_request = tts_service_pb2.TTSRequest(
                user_id=self.user_id,
                text=text,
                voice_id=self.voice_id,
                language=self.language,
                device_type="cooking",
                is_final=1,  # 最终版本
                mp3_id="",
                play_mp3="",
                uuid=uuid_str,
                topic="cooking_advice"
            )
            
            # 创建服务请求
            service_request = tts_service_pb2.TTSServiceRequest(tts_request=tts_request)
            
            # 调用TTS服务
            audio_chunks = []
            async for response in self.tts_stub.ProcessTTS(service_request):
                if response.HasField('audio_response'):
                    audio_data = response.audio_response.audio_data
                    if audio_data:
                        audio_chunks.append(audio_data)
                        self.stats['total_pcm_bytes'] += len(audio_data)
            
            logger.info(f"🎵 TTS服务返回 {len(audio_chunks)} 个音频块")
            return audio_chunks
            
        except Exception as e:
            logger.error(f"❌ TTS服务调用失败: {e}")
            return []
    
    async def _call_tts_service_streaming(self, text: str) -> List[bytes]:
        """流式调用TTS服务"""
        try:
            # 生成UUID
            uuid_str = f"cooking_stream_{uuid.uuid4().hex[:8]}"
            
            # 分步调用TTS服务 (is_final: 1, 2, 3)
            audio_chunks = []
            
            for is_final in [1, 2, 3]:
                tts_request = tts_service_pb2.TTSRequest(
                    user_id=self.user_id,
                    text=text,
                    voice_id=self.voice_id,
                    language=self.language,
                    device_type="cooking",
                    is_final=is_final,
                    mp3_id="",
                    play_mp3="",
                    uuid=uuid_str,
                    topic="cooking_advice"
                )
                
                service_request = tts_service_pb2.TTSServiceRequest(tts_request=tts_request)
                
                async for response in self.tts_stub.ProcessTTS(service_request):
                    if response.HasField('audio_response'):
                        audio_data = response.audio_response.audio_data
                        if audio_data:
                            audio_chunks.append(audio_data)
                            self.stats['total_pcm_bytes'] += len(audio_data)
                
                logger.info(f"🔄 流式TTS步骤 {is_final} 完成")
            
            logger.info(f"🎵 流式TTS服务返回 {len(audio_chunks)} 个音频块")
            return audio_chunks
            
        except Exception as e:
            logger.error(f"❌ 流式TTS服务调用失败: {e}")
            return []
    
    async def _send_audio_to_downlink(self, audio_chunks: List[bytes], task_id: str) -> bool:
        """发送音频到downlink服务"""
        try:
            logger.info(f"📡 发送 {len(audio_chunks)} 个音频块到downlink服务")
            
            for i, audio_chunk in enumerate(audio_chunks):
                # 创建音频消息请求
                audio_request = downlink_pb2.AudioMessageRequest(
                    device_id=self.device_id,
                    user_id=self.user_id,
                    audio_data=audio_chunk,
                    sample_rate=self.sample_rate,
                    channels=self.channels,
                    bit_depth=self.bit_depth,
                    task_id=task_id,
                    priority=downlink_pb2.PRIORITY_MEDIUM,
                    is_end=(i == len(audio_chunks) - 1)  # 最后一个块标记为结束
                )
                
                # 发送音频消息
                response = await self.downlink_stub.SendAudioMessage(audio_request)
                
                if response.success:
                    self.stats['audio_chunks_sent'] += 1
                    logger.debug(f"✅ 音频块 {i+1}/{len(audio_chunks)} 发送成功")
                else:
                    logger.error(f"❌ 音频块 {i+1} 发送失败: {response.error_message}")
                    return False
            
            logger.info(f"✅ 所有音频块发送完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 发送音频到downlink失败: {e}")
            return False
    
    async def _send_audio_stream_to_downlink(self, audio_chunks: List[bytes], task_id: str, stream_session_id: str) -> bool:
        """流式发送音频到downlink服务"""
        try:
            logger.info(f"📡 流式发送 {len(audio_chunks)} 个音频块到downlink服务")
            
            async def stream_generator():
                for i, audio_chunk in enumerate(audio_chunks):
                    # 创建流式音频消息请求
                    stream_request = downlink_pb2.StreamAudioMessageRequest(
                        device_id=self.device_id,
                        user_id=self.user_id,
                        audio_data=audio_chunk,
                        sample_rate=self.sample_rate,
                        channels=self.channels,
                        bit_depth=self.bit_depth,
                        task_id=task_id,
                        priority=downlink_pb2.PRIORITY_MEDIUM,
                        sequence_number=i,
                        is_end=(i == len(audio_chunks) - 1),
                        stream_session_id=stream_session_id
                    )
                    
                    yield stream_request
                    self.stats['audio_chunks_sent'] += 1
                    logger.debug(f"🔄 流式音频块 {i+1}/{len(audio_chunks)} 发送")
            
            # 流式发送
            response = await self.downlink_stub.StreamAudioMessage(stream_generator())
            
            if response.success:
                logger.info(f"✅ 流式音频发送完成")
                return True
            else:
                logger.error(f"❌ 流式音频发送失败: {response.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 流式发送音频失败: {e}")
            return False
    
    async def cancel_current_task(self):
        """取消当前任务"""
        if not self.current_task_id:
            logger.warning("⚠️ 没有正在执行的任务")
            return False
        
        try:
            cancel_request = downlink_pb2.CancelTaskRequest(
                device_id=self.device_id,
                user_id=self.user_id,
                task_id=self.current_task_id
            )
            
            response = await self.downlink_stub.CancelTask(cancel_request)
            
            if response.success:
                logger.info(f"✅ 任务 {self.current_task_id} 已取消")
                self.current_task_id = None
                return True
            else:
                logger.error(f"❌ 取消任务失败: {response.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 取消任务异常: {e}")
            return False
    
    def get_stats(self):
        """获取统计信息"""
        stats = self.stats.copy()
        if stats['start_time'] and stats['end_time']:
            stats['duration'] = stats['end_time'] - stats['start_time']
        return stats
    
    def set_voice_params(self, voice_id: str = None, language: str = None):
        """设置语音参数"""
        if voice_id:
            self.voice_id = voice_id
        if language:
            self.language = language
        logger.info(f"🎤 语音参数已更新: voice_id={self.voice_id}, language={self.language}")

# 全局TTS管理器实例
_tts_manager = None

async def get_tts_manager() -> CookingTTSManager:
    """获取全局TTS管理器实例"""
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = CookingTTSManager()
        await _tts_manager.connect()
    return _tts_manager

async def speak_cooking_advice(text: str, mode: TTSMode = TTSMode.SIMPLE):
    """为烹饪建议播放语音"""
    manager = await get_tts_manager()
    return await manager.speak_text(text, mode)

async def stop_current_speech():
    """停止当前语音播放"""
    manager = await get_tts_manager()
    return await manager.cancel_current_task() 