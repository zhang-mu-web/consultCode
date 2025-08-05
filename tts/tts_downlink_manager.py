#!/usr/bin/env python3
"""
TTS到Downlink流程管理器
支持不同的调用模式，保持模块解耦
"""

import os
import sys
import asyncio
import time
import json
import logging
import random
import numpy as np
import uuid
from typing import List, Optional, Callable
from enum import Enum


import grpc
# import tts_service_pb2
# import tts_service_pb2_grpc
# import downlink_pb2 as downlink_pb2
# import downlink_pb2_grpc as downlink_grpc


from tts import tts_service_pb2, tts_service_pb2_grpc
from tts import downlink_pb2
from tts import downlink_pb2_grpc as downlink_grpc


# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TTSFlowMode(Enum):
    """TTS流程模式"""
    SIMPLE = "simple"           # 简单模式：直接调用TTS，然后发送音频
    STEPPED = "stepped"         # 分步模式：按is_final=1,2,3的顺序调用
    STREAMING = "streaming"     # 流式模式：实时处理音频流

class TTSDownlinkManager:
    """TTS到Downlink流程管理器"""
    
    def __init__(self, tts_endpoint='192.168.2.109:50051', downlink_endpoint='192.168.2.88:50055'):
        self.tts_endpoint = tts_endpoint
        self.downlink_endpoint = downlink_endpoint
        
        # 用户和设备ID - 按照tts_to_downlink_example.py的设置
        self.user_id = "537971611258480000"
        self.device_id = "537971611258480000"
        
        # gRPC连接
        self.tts_channel = None
        self.tts_stub = None
        self.downlink_channel = None
        self.downlink_stub = None
        
        # 音频参数
        self.sample_rate = 16000
        self.channels = 1
        self.frame_size = 960  # 60ms @ 16kHz
        
        # 统计信息
        self.stats = {
            'tts_calls': 0,
            'audio_chunks_sent': 0,
            'total_pcm_bytes': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def setup_connections(self):
        """建立gRPC连接"""
        try:
            # 连接TTS服务
            self.tts_channel = grpc.aio.insecure_channel(self.tts_endpoint)
            self.tts_stub = tts_service_pb2_grpc.TTSServiceStub(self.tts_channel)
            
            # 连接downlink服务
            self.downlink_channel = grpc.aio.insecure_channel(self.downlink_endpoint)
            self.downlink_stub = downlink_grpc.DownlinkServiceStub(self.downlink_channel)
            
            logger.info(f"✅ gRPC连接建立成功")
            logger.info(f"   TTS服务: {self.tts_endpoint}")
            logger.info(f"   Downlink服务: {self.downlink_endpoint}")
            return True
            
        except Exception as e:
            logger.error(f"❌ gRPC连接失败: {e}")
            return False
    
    async def close_connections(self):
        """关闭gRPC连接"""
        if self.tts_channel:
            await self.tts_channel.close()
        if self.downlink_channel:
            await self.downlink_channel.close()
        logger.info("🔌 gRPC连接已关闭")
    
    def _generate_unique_uuid(self, prefix: str = "tts") -> str:
        """生成唯一的UUID"""
        timestamp = int(time.time() * 1000)  # 毫秒级时间戳
        random_suffix = random.randint(1000, 9999)
        return f"{prefix}_{timestamp}_{random_suffix}"
    
    async def process_tts_request(self, text: str, user_id: str, mode: TTSFlowMode = TTSFlowMode.SIMPLE, 
                                voice_id: str = "1", language: str = "zh"):
        """
        处理TTS请求（支持多种模式）
        
        Args:
            text: 要合成的文本
            user_id: 用户ID
            mode: 流程模式
            voice_id: 音色ID
            language: 语言代码
        """
        try:
            self.stats['start_time'] = time.time()
            
            # 为整个TTS请求生成统一的task_id
            task_id = str(uuid.uuid4())
            logger.info(f"🎯 生成统一Task ID: {task_id}")
            
            if mode == TTSFlowMode.SIMPLE:
                await self._process_simple_mode(text, user_id, voice_id, language, task_id)
            elif mode == TTSFlowMode.STEPPED:
                await self._process_stepped_mode(text, user_id, voice_id, language, task_id)
            elif mode == TTSFlowMode.STREAMING:
                await self._process_streaming_mode(text, user_id, voice_id, language, task_id)
            else:
                raise ValueError(f"不支持的流程模式: {mode}")
            
            self.stats['end_time'] = time.time()
            duration = self.stats['end_time'] - self.stats['start_time']
            
            logger.info(f"✅ TTS请求处理完成 (模式: {mode.value})")
            logger.info(f"   总耗时: {duration:.2f} 秒")
            logger.info(f"   音频块数: {self.stats['audio_chunks_sent']}")
            logger.info(f"   PCM总大小: {self.stats['total_pcm_bytes']} 字节")
            
        except Exception as e:
            logger.error(f"❌ 处理TTS请求失败: {e}")
    
    async def process_tts_to_downlink(self, text: str, voice_id: str = "1", language: str = "zh"):
        """统一的主处理方法 - 使用分块发送，按照tts_to_downlink_example.py的逻辑"""
        try:
            logger.info("🚀 开始TTS到Downlink分块处理流程")
            start_time = time.time()
            
            # 1. 先调用TTS服务生成所有音频块
            audio_chunks = await self._call_tts_service(text, self.user_id, voice_id, language)
            
            if not audio_chunks:
                logger.error("❌ 没有生成音频数据")
                return False
            
            # 2. 使用分块方法发送音频
            success = await self._send_audio_to_downlink(audio_chunks, self.user_id)
            
            end_time = time.time()
            duration = end_time - start_time
            
            if success:
                logger.info(f"✅ TTS到Downlink分块处理完成，耗时: {duration:.2f} 秒")
            else:
                logger.error(f"❌ TTS到Downlink分块处理失败")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 处理流程异常: {e}")
            return False
    
    def get_stats(self):
        """获取统计信息"""
        return self.stats.copy()
    
    async def _process_simple_mode(self, text: str, user_id: str, voice_id: str, language: str, task_id: str):
        """简单模式：使用与tts_to_downlink_example.py相同的逻辑"""
        logger.info(f"🎯 使用简单模式处理TTS请求")
        
        # 直接使用流式处理方法，确保逻辑一致
        topic = f"tts/doll/{user_id}"
        return await self._stream_audio_processing(text, user_id, voice_id, language, topic, task_id)
    
    async def _process_stepped_mode(self, text: str, user_id: str, voice_id: str, language: str, task_id: str):
        """分步模式：使用与tts_to_downlink_example.py相同的逻辑"""
        logger.info(f"🔄 使用分步模式处理TTS请求")
        
        # 直接使用流式处理方法，确保逻辑一致
        topic = f"tts/doll/{user_id}"
        return await self._stream_audio_processing(text, user_id, voice_id, language, topic, task_id)
    
    async def _process_streaming_mode(self, text: str, user_id: str, voice_id: str, language: str, task_id: str):
        """流式模式处理"""
        logger.info(f"🌊 使用流式模式处理TTS请求")
        
        # 使用新的实时流式处理方法
        topic = f"tts/doll/{user_id}"
        return await self._stream_audio_processing(text, user_id, voice_id, language, topic, task_id)
    
    async def _call_tts_service(self, text: str, user_id: str, voice_id: str, language: str) -> List[bytes]:
        """调用TTS服务 - 按照tts_to_downlink_example.py的逻辑"""
        try:
            # 生成唯一UUID
            uuid_str = self._generate_unique_uuid("tts_call")
            
            logger.info(f"📞 调用TTS服务 - 用户: {user_id}, 文本: '{text[:50]}...'")
            
            # 创建TTS请求
            tts_request = tts_service_pb2.TTSRequest(
                user_id=user_id,
                text=text,
                voice_id=voice_id,
                language=language,
                device_type="doll",
                is_final=2,  # 直接处理
                mp3_id="0",
                play_mp3="0",
                uuid=uuid_str,
                topic=f"tts/doll/{user_id}"
            )
            
            service_request = tts_service_pb2.TTSServiceRequest(tts_request=tts_request)
            
            # 调用TTS服务
            audio_chunks = []
            response_stream = self.tts_stub.ProcessTTS(service_request)
            
            async for response in response_stream:
                if response.HasField('audio_response'):
                    audio_data = response.audio_response.audio_data
                    if audio_data:
                        audio_chunks.append(audio_data)
                        logger.info(f"📦 接收到音频块 {len(audio_chunks)}: {len(audio_data)} 字节")
                elif response.HasField('status_response'):
                    status = response.status_response
                    logger.info(f"📊 TTS状态: {status.state} - {status.message}")
                    if status.state == "error":
                        logger.error(f"❌ TTS服务返回错误")
                        return []
            
            logger.info(f"✅ TTS调用完成，生成 {len(audio_chunks)} 个音频块")
            return audio_chunks
            
        except Exception as e:
            logger.error(f"❌ TTS服务调用失败: {e}")
            return []
    
    async def _send_tts_request(self, user_id: str, text: str, voice_id: str, language: str, uuid_str: str, is_final: int) -> List[bytes]:
        """发送TTS请求"""
        try:
            logger.info(f"📤 发送TTS请求 - 用户: {user_id}, 文本: '{text}', is_final: {is_final}, UUID: {uuid_str}")
            
            # 创建TTS请求
            tts_request = tts_service_pb2.TTSRequest(
                user_id=user_id,
                text=text,
                voice_id=voice_id,
                language=language,
                device_type="doll",
                is_final=is_final,
                mp3_id="0",
                play_mp3="0",
                uuid=uuid_str,
                topic=f"tts/doll/{user_id}"  # 修复topic格式
            )
            
            service_request = tts_service_pb2.TTSServiceRequest(tts_request=tts_request)
            response_stream = self.tts_stub.ProcessTTS(service_request)
            
            audio_chunks = []
            chunk_count = 0
            
            async for response in response_stream:
                if response.HasField('audio_response'):
                    audio_data = response.audio_response.audio_data
                    if audio_data:
                        audio_chunks.append(audio_data)
                        chunk_count += 1
                        self.stats['total_pcm_bytes'] += len(audio_data)
                        
                        if chunk_count <= 3 or chunk_count % 10 == 0:
                            logger.info(f"📦 收到音频块 {chunk_count}: {len(audio_data)} 字节")
                
                elif response.HasField('status_response'):
                    status = response.status_response
                    logger.info(f"📊 状态更新: {status.state} - {status.message}")
            
            return audio_chunks
            
        except Exception as e:
            logger.error(f"❌ 发送TTS请求失败: {e}")
            return []
    
    async def _stream_audio_processing(self, text: str, user_id: str, voice_id: str, language: str, topic: str, task_id: str):
        """流式音频处理 - 实现真正的流式TTS到Downlink"""
        try:
            logger.info(f"🎤 开始流式TTS到Downlink处理: {text}")
            logger.info(f"   TTS服务地址: {self.tts_endpoint}")
            logger.info(f"   用户ID: {user_id}")
            logger.info(f"   音色ID: {voice_id}")
            logger.info(f"   语言: {language}")
            logger.info(f"   Task ID: {task_id}")
            
            # 生成流式会话ID
            stream_session_id = str(uuid.uuid4())
            
            # 创建流式请求生成器
            async def stream_generator():
                sequence_number = 0
                chunk_count = 0
                last_audio_time = time.time()
                end_frame_sent = False
                
                try:
                    # 生成TTS请求的UUID
                    uuid_str = self._generate_unique_uuid("tts_stream")
                    
                    # 创建TTS请求
                    tts_request = tts_service_pb2.TTSRequest(
                        user_id=user_id,
                        text=text,
                        voice_id=voice_id,
                        language=language,
                        device_type="doll",
                        is_final=2,
                        mp3_id="0",
                        play_mp3="0",
                        uuid=uuid_str,
                        topic=f"tts/doll/{user_id}"
                    )
                    
                    service_request = tts_service_pb2.TTSServiceRequest(tts_request=tts_request)
                    
                    logger.info(f"📞 开始TTS流式处理")
                    
                    # 流式处理TTS响应
                    async for response in self.tts_stub.ProcessTTS(service_request):
                        if response.HasField('audio_response'):
                            audio_data = response.audio_response.audio_data
                            if audio_data:
                                chunk_count += 1
                                last_audio_time = time.time()
                                logger.info(f"📦 接收到音频块 {chunk_count}: {len(audio_data)} 字节")
                                
                                # 立即发送音频块到downlink
                                stream_request = downlink_pb2.StreamAudioMessageRequest(
                                    device_id=self.device_id,
                                    user_id=user_id,
                                    audio_data=audio_data,
                                    sample_rate=16000,
                                    channels=1,
                                    bit_depth=16,
                                    task_id=task_id,
                                    priority=downlink_pb2.PRIORITY_MEDIUM,
                                    sequence_number=sequence_number,
                                    is_end=False,
                                    stream_session_id=stream_session_id
                                )
                                
                                logger.info(f"📤 发送音频块 {sequence_number}: {len(audio_data)} 字节")
                                yield stream_request
                                sequence_number += 1
                                
                                # 添加小延迟，模拟音频播放时间
                                await asyncio.sleep(0.05)  # 50ms延迟
                                
                        elif response.HasField('status_response'):
                            status = response.status_response
                            logger.info(f"📊 TTS状态: {status.state}")
                            
                            # 检查结束状态
                            if status.state in ["completed", "finished", "done", "end"]:
                                logger.info(f"🎯 TTS完成，状态: {status.state}")
                                break
                            elif status.state in ["error", "failed", "cancelled"]:
                                logger.error(f"❌ TTS处理失败，状态: {status.state}")
                                break
                    
                    # 等待一段时间确保音频播放完成
                    if chunk_count > 0:
                        # 计算音频总时长（假设16kHz采样率，每个音频块约60ms）
                        estimated_duration = chunk_count * 0.06  # 60ms per chunk
                        wait_time = max(estimated_duration * 0.5, 0.5)  # 等待音频播放完成
                        logger.info(f"⏳ 等待音频播放完成，预计时长: {estimated_duration:.2f}秒，等待: {wait_time:.2f}秒")
                        await asyncio.sleep(wait_time)
                    
                    # 发送结束帧
                    end_request = downlink_pb2.StreamAudioMessageRequest(
                        device_id=self.device_id,
                        user_id=user_id,
                        audio_data=b"",
                        sample_rate=16000,
                        channels=1,
                        bit_depth=16,
                        task_id=task_id,
                        priority=downlink_pb2.PRIORITY_MEDIUM,
                        sequence_number=sequence_number,
                        is_end=True,
                        stream_session_id=stream_session_id
                    )
                    
                    logger.info(f"🎯 发送结束帧，序列号: {sequence_number}")
                    yield end_request
                    end_frame_sent = True
                    
                except Exception as e:
                    logger.error(f"❌ 流式处理异常: {e}")
                    # 即使发生异常，也要发送结束帧
                    if not end_frame_sent:
                        end_request = downlink_pb2.StreamAudioMessageRequest(
                            device_id=self.device_id,
                            user_id=user_id,
                            audio_data=b"",
                            sample_rate=16000,
                            channels=1,
                            bit_depth=16,
                            task_id=task_id,
                            priority=downlink_pb2.PRIORITY_MEDIUM,
                            sequence_number=sequence_number,
                            is_end=True,
                            stream_session_id=stream_session_id
                        )
                        yield end_request
                        logger.info("✅ 异常情况下结束帧已发送")
                    raise
                finally:
                    # 确保在流结束时发送结束帧（如果还没有发送的话）
                    if chunk_count > 0 and not end_frame_sent:
                        logger.warning("⚠️ 检测到音频流结束但未发送结束帧，强制发送")
                        end_request = downlink_pb2.StreamAudioMessageRequest(
                            device_id=self.device_id,
                            user_id=user_id,
                            audio_data=b"",
                            sample_rate=16000,
                            channels=1,
                            bit_depth=16,
                            task_id=task_id,
                            priority=downlink_pb2.PRIORITY_MEDIUM,
                            sequence_number=sequence_number,
                            is_end=True,
                            stream_session_id=stream_session_id
                        )
                        yield end_request
                        logger.info("✅ 强制发送结束帧完成")
            
            # 调用downlink流式接口
            logger.info(f"📤 调用Downlink流式接口")
            response = await self.downlink_stub.StreamAudioMessage(stream_generator())
            
            if response.success:
                logger.info(f"✅ 流式音频处理成功: {response.message}")
                return True
            else:
                logger.error(f"❌ 流式音频处理失败: {response.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 流式音频处理异常: {e}")
            return False
    
    async def _send_audio_stream(self, topic: str, audio_chunks: List[bytes], task_id: str = None):
        """使用流式方法发送音频流"""
        try:
            # 从topic中提取user_id，格式通常是 "tts/doll/{user_id}"
            user_id = topic.split('/')[-1] if '/' in topic else "unknown"
            
            # 如果没有提供task_id，则生成一个
            if task_id is None:
                task_id = f"tts_stream_{int(time.time() * 1000)}"
            
            # 生成流式会话ID
            stream_session_id = str(uuid.uuid4())
            
            logger.info(f"📤 通过流式服务发送音频流: topic={topic} chunks={len(audio_chunks)}")
            logger.info(f"   Task ID: {task_id}")
            logger.info(f"   Stream Session ID: {stream_session_id}")
            
            # 创建流式请求生成器
            async def stream_generator():
                sequence_number = 0
                
                for i, audio_chunk in enumerate(audio_chunks):
                    try:
                        # 创建流式请求
                        stream_request = downlink_pb2.StreamAudioMessageRequest(
                            device_id="doll",
                            user_id=user_id,
                            audio_data=audio_chunk,
                            sample_rate=self.sample_rate,
                            channels=self.channels,
                            bit_depth=16,
                            task_id=task_id,
                            priority=downlink_pb2.PRIORITY_MEDIUM,
                            sequence_number=sequence_number,
                            is_end=False,
                            stream_session_id=stream_session_id
                        )
                        
                        logger.debug(f"📦 发送音频块 {i+1}/{len(audio_chunks)}: {len(audio_chunk)} 字节")
                        yield stream_request
                        sequence_number += 1
                        
                        await asyncio.sleep(0.01)
                        
                    except Exception as e:
                        logger.error(f"❌ 生成音频块 {i+1} 异常: {e}")
                        raise
                
                # 发送结束帧
                end_request = downlink_pb2.StreamAudioMessageRequest(
                    device_id="doll",
                    user_id=user_id,
                    audio_data=b"",
                    sample_rate=self.sample_rate,
                    channels=self.channels,
                    bit_depth=16,
                    task_id=task_id,
                    priority=downlink_pb2.PRIORITY_MEDIUM,
                    sequence_number=sequence_number,
                    is_end=True,
                    stream_session_id=stream_session_id
                )
                
                logger.info(f"🎯 发送结束帧，序列号: {sequence_number}")
                yield end_request
            
            # 调用流式接口
            response = await self.downlink_stub.StreamAudioMessage(stream_generator())
            
            if response.success:
                logger.info(f"✅ 音频流发送成功: topic={topic} chunks={len(audio_chunks)}")
                self.stats['audio_chunks_sent'] += len(audio_chunks)
            else:
                logger.error(f"❌ 音频流发送失败: {response.error_message}")
            
        except Exception as e:
            logger.error(f"❌ 发送音频流异常: {e}")
    
    async def _send_tts_control_message(self, topic: str, state: str):
        """发送TTS控制消息"""
        try:
            # 从topic中提取user_id，格式通常是 "tts/doll/{user_id}"
            user_id = topic.split('/')[-1] if '/' in topic else "unknown"
            
            control_payload = {
                "type": "tts",
                "state": state,
                "_mqtt_send_time": int(time.time() * 1000)
            }
            
            request = downlink_pb2.TextMessageRequest(
                device_id="doll",  # 设备ID
                user_id=user_id,   # 用户ID
                text_content=json.dumps(control_payload, ensure_ascii=False),  # 控制消息文本
                task_id=f"tts_control_{int(time.time() * 1000)}",  # 任务ID
                priority=downlink_pb2.PRIORITY_MEDIUM  # 优先级
            )
            
            response = await self.downlink_stub.SendTextMessage(request)
            if response.success:
                logger.info(f"🎬 TTS控制消息发送成功: {topic} state={state}")
            else:
                logger.error(f"❌ TTS控制消息发送失败: {topic} state={state} error={response.error_message}")
                
        except Exception as e:
            logger.error(f"❌ 发送TTS控制消息异常: {topic} state={state} error={e}")
    
    async def _send_audio_chunks(self, topic: str, audio_chunks: List[bytes]):
        """发送音频数据块"""
        try:
            # 为整个音频会话生成一个固定的task_id
            task_id = str(uuid.uuid4())
            
            for i, audio_chunk in enumerate(audio_chunks):
                await self._send_audio_chunk(topic, audio_chunk, task_id)
                
                # 记录发送进度
                if (i + 1) <= 3 or (i + 1) % 10 == 0 or (i + 1) == len(audio_chunks):
                    logger.info(f"📤 发送音频块 {i+1}/{len(audio_chunks)}: {len(audio_chunk)} 字节")
                
                # 模拟实时播放间隔（可选）
                await asyncio.sleep(0.01)  # 10ms间隔
                
        except Exception as e:
            logger.error(f"❌ 发送音频块异常: {e}")
    
    async def _send_audio_chunk(self, topic: str, audio_chunk: bytes, task_id: str = None):
        """发送单个音频块 - 使用流式方法"""
        try:
            # 从topic中提取user_id，格式通常是 "tts/doll/{user_id}"
            user_id = topic.split('/')[-1] if '/' in topic else "unknown"
            
            # 如果没有提供task_id，则生成一个
            if task_id is None:
                task_id = str(uuid.uuid4())
            
            # 生成流式会话ID
            stream_session_id = str(uuid.uuid4())
            
            # 创建流式请求生成器
            async def stream_generator():
                # 发送音频块
                stream_request = downlink_pb2.StreamAudioMessageRequest(
                    device_id="doll",
                    user_id=user_id,
                    audio_data=audio_chunk,
                    sample_rate=16000,
                    channels=1,
                    bit_depth=16,
                    task_id=task_id,
                    priority=downlink_pb2.PRIORITY_MEDIUM,
                    sequence_number=0,
                    is_end=False,
                    stream_session_id=stream_session_id
                )
                yield stream_request
                
                # 发送结束帧
                end_request = downlink_pb2.StreamAudioMessageRequest(
                    device_id="doll",
                    user_id=user_id,
                    audio_data=b"",
                    sample_rate=16000,
                    channels=1,
                    bit_depth=16,
                    task_id=task_id,
                    priority=downlink_pb2.PRIORITY_MEDIUM,
                    sequence_number=1,
                    is_end=True,
                    stream_session_id=stream_session_id
                )
                yield end_request
            
            # 调用流式接口
            response = await self.downlink_stub.StreamAudioMessage(stream_generator())
            
            if response.success:
                return True
            else:
                logger.error(f"❌ 音频块发送失败: {response.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 发送音频块异常: {e}")
            return False
    
    async def _send_single_audio_chunk_realtime(self, user_id: str, audio_chunk: bytes, task_id: str):
        """发送单个音频块到downlink - 使用流式方法"""
        try:
            # 生成流式会话ID
            stream_session_id = str(uuid.uuid4())
            
            # 创建流式请求生成器
            async def stream_generator():
                # 发送音频块
                stream_request = downlink_pb2.StreamAudioMessageRequest(
                    device_id=self.device_id,
                    user_id=user_id,
                    audio_data=audio_chunk,
                    sample_rate=16000,
                    channels=1,
                    bit_depth=16,
                    task_id=task_id,
                    priority=downlink_pb2.PRIORITY_MEDIUM,
                    sequence_number=0,
                    is_end=False,
                    stream_session_id=stream_session_id
                )
                yield stream_request
                
                # 发送结束帧
                end_request = downlink_pb2.StreamAudioMessageRequest(
                    device_id=self.device_id,
                    user_id=user_id,
                    audio_data=b"",
                    sample_rate=16000,
                    channels=1,
                    bit_depth=16,
                    task_id=task_id,
                    priority=downlink_pb2.PRIORITY_MEDIUM,
                    sequence_number=1,
                    is_end=True,
                    stream_session_id=stream_session_id
                )
                yield end_request
            
            # 调用流式接口
            response = await self.downlink_stub.StreamAudioMessage(stream_generator())
            
            if response.success:
                return True
            else:
                logger.error(f"❌ 音频块发送失败: {response.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 发送音频块异常: {e}")
            return False
    
    async def _send_audio_to_downlink(self, audio_chunks, user_id: str, task_id: str = None):
        """使用流式方法发送音频到downlink - 按照test_single_stream.py的逻辑"""
        try:
            if not audio_chunks:
                logger.warning("⚠️ 没有音频数据可发送")
                return False
            
            if task_id is None:
                task_id = str(uuid.uuid4())
            
            # 生成流式会话ID
            stream_session_id = str(uuid.uuid4())
            
            logger.info(f"📤 通过downlink流式服务发送音频")
            logger.info(f"   Task ID: {task_id}")
            logger.info(f"   Stream Session ID: {stream_session_id}")
            
            # 创建流式请求生成器
            async def stream_generator():
                sequence_number = 0
                
                for i, audio_chunk in enumerate(audio_chunks):
                    try:
                        # 创建流式请求
                        stream_request = downlink_pb2.StreamAudioMessageRequest(
                            device_id=self.device_id,
                            user_id=user_id,
                            audio_data=audio_chunk,
                            sample_rate=16000,
                            channels=1,
                            bit_depth=16,
                            task_id=task_id,
                            priority=downlink_pb2.PRIORITY_MEDIUM,
                            sequence_number=sequence_number,
                            is_end=False,
                            stream_session_id=stream_session_id
                        )
                        logger.info(f"sequence_number: {sequence_number}")
                        logger.info(f"📦 发送音频块 {i+1}/{len(audio_chunks)}: {len(audio_chunk)} 字节")
                        yield stream_request
                        sequence_number += 1
                        
                        await asyncio.sleep(0.01)
                        
                    except Exception as e:
                        logger.error(f"❌ 生成音频块 {i+1} 异常: {e}")
                        raise
                
                # 发送结束帧
                end_request = downlink_pb2.StreamAudioMessageRequest(
                    device_id=self.device_id,
                    user_id=user_id,
                    audio_data=b"",
                    sample_rate=16000,
                    channels=1,
                    bit_depth=16,
                    task_id=task_id,
                    priority=downlink_pb2.PRIORITY_MEDIUM,
                    sequence_number=sequence_number,
                    is_end=True,
                    stream_session_id=stream_session_id
                )
                
                logger.info(f"🎯 发送结束帧，序列号: {sequence_number}")
                yield end_request
            
            # 调用流式接口
            response = await self.downlink_stub.StreamAudioMessage(stream_generator())
            
            if response.success:
                logger.info(f"✅ 流式音频发送成功: {response.message}")
                return True
            else:
                logger.error(f"❌ 流式音频发送失败: {response.error_message}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Downlink流式服务调用失败: {e}")
            return False
    

async def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description="TTS到Downlink流程管理器")
    parser.add_argument('--tts-server', default='192.168.2.109:50051', help='TTS服务地址')
    parser.add_argument('--downlink-server', default='192.168.2.88:50055', help='Downlink服务地址')
    parser.add_argument('--text', default='你好，这是TTS到Downlink流程管理器的测试。', help='要合成的文本')
    parser.add_argument('--user-id', default='test_manager_001', help='用户ID')
    parser.add_argument('--voice-id', default='1', help='音色ID')
    parser.add_argument('--language', default='zh', help='语言代码')
    parser.add_argument('--mode', default='simple', choices=['simple', 'stepped', 'streaming'], 
                       help='流程模式: simple(简单), stepped(分步), streaming(流式)')
    
    args = parser.parse_args()
    
    # 解析模式
    mode_map = {
        'simple': TTSFlowMode.SIMPLE,
        'stepped': TTSFlowMode.STEPPED,
        'streaming': TTSFlowMode.STREAMING
    }
    mode = mode_map[args.mode]
    
    # 创建管理器
    manager = TTSDownlinkManager(args.tts_server, args.downlink_server)
    
    try:
        # 建立连接
        if not await manager.setup_connections():
            logger.error("❌ 连接失败，退出")
            return
        
        # 处理TTS请求
        await manager.process_tts_request(
            text=args.text,
            user_id=args.user_id,
            mode=mode,
            voice_id=args.voice_id,
            language=args.language
        )
        
        # 打印统计信息
        stats = manager.get_stats()
        logger.info("\n=== 统计信息 ===")
        logger.info(f"流程模式: {mode.value}")
        logger.info(f"TTS调用次数: {stats['tts_calls']}")
        logger.info(f"发送音频块数: {stats['audio_chunks_sent']}")
        logger.info(f"PCM总大小: {stats['total_pcm_bytes']} 字节")
        if 'total_duration' in stats:
            logger.info(f"总耗时: {stats['total_duration']:.2f} 秒")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ 用户中断")
    except Exception as e:
        logger.error(f"❌ 程序异常: {e}")
    finally:
        await manager.close_connections()

if __name__ == "__main__":
    asyncio.run(main()) 