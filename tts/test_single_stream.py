#!/usr/bin/env python3
"""
单个音频流测试
专门测试一个完整的TTS流式到Downlink流式音频传输
"""

import asyncio
import logging
import uuid
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 导入gRPC模块
import grpc
import tts.tts_service_pb2 as tts_pb2
import tts.tts_service_pb2_grpc as tts_grpc
import downlink_pb2
import downlink_pb2_grpc as downlink_grpc

async def test_single_audio_stream():
    """测试单个音频流"""
    
    # 配置参数
    tts_endpoint = '192.168.2.109:50051'
    downlink_endpoint = 'localhost:50055'
    user_id = "179437604591560000"
    device_id = "179437604591560000"
    test_text = "你好，这是一个完整的音频流测试。"
    
    logger.info("🚀 开始单个音频流测试")
    logger.info(f"TTS服务: {tts_endpoint}")
    logger.info(f"Downlink服务: {downlink_endpoint}")
    logger.info(f"测试文本: {test_text}")
    logger.info(f"用户ID: {user_id}")
    logger.info(f"设备ID: {device_id}")
    
    try:
        # 建立连接
        tts_channel = grpc.aio.insecure_channel(tts_endpoint)
        tts_stub = tts_grpc.TTSServiceStub(tts_channel)
        
        downlink_channel = grpc.aio.insecure_channel(downlink_endpoint)
        downlink_stub = downlink_grpc.DownlinkServiceStub(downlink_channel)
        
        logger.info("✅ gRPC连接建立成功")
        
        # 生成唯一标识 - 整个流式会话使用相同的标识
        task_id = str(uuid.uuid4())  # 同一个流式请求使用相同的task_id
        stream_session_id = str(uuid.uuid4())
        uuid_str = f"tts_{int(time.time() * 1000)}"
        
        logger.info(f"📋 会话信息:")
        logger.info(f"   Task ID: {task_id}")
        logger.info(f"   Stream Session ID: {stream_session_id}")
        logger.info(f"   TTS UUID: {uuid_str}")
        
        # 创建TTS请求
        tts_request = tts_pb2.TTSRequest(
            user_id=user_id,
            text=test_text,
            voice_id="1",
            language="zh",
            device_type="doll",
            is_final=2,
            mp3_id="0",
            play_mp3="0",
            uuid=uuid_str,
            topic=f"tts/doll/{user_id}"
        )
        
        service_request = tts_pb2.TTSServiceRequest(tts_request=tts_request)
        
        # 创建Downlink流式请求生成器
        async def stream_generator():
            sequence_number = 0
            chunk_count = 0
            last_audio_time = time.time()
            end_frame_sent = False  # 标记是否已发送结束帧
            
            logger.info("📤 开始TTS流式处理...")
            
            try:
                async for response in tts_stub.ProcessTTS(service_request):
                    if response.HasField('audio_response'):
                        audio_data = response.audio_response.audio_data
                        if audio_data:
                            chunk_count += 1
                            last_audio_time = time.time()  # 更新最后音频时间
                            logger.info(f"📦 音频块 {sequence_number}: {len(audio_data)} 字节")
                            
                            # 创建Downlink流式请求 - 使用相同的task_id
                            stream_request = downlink_pb2.StreamAudioMessageRequest(
                                device_id=device_id,
                                user_id=user_id,
                                audio_data=audio_data,
                                sample_rate=16000,
                                channels=1,
                                bit_depth=16,
                                task_id=task_id,  # 使用相同的task_id
                                priority=downlink_pb2.PRIORITY_MEDIUM,
                                sequence_number=sequence_number,
                                is_end=False,
                                stream_session_id=stream_session_id
                            )
                            
                            yield stream_request
                            sequence_number += 1
                            
                            
                    elif response.HasField('status_response'):
                        status = response.status_response
                        logger.info(f"📊 TTS状态: {status.state}")
                        # 添加详细的状态信息
                        logger.info(f"📋 TTS状态详情: state={status.state}, 完整响应={response}")
                        
                        # 检查各种结束状态
                        if status.state in ["completed", "finished", "done", "end"]:
                            logger.info(f"🎯 TTS完成，状态: {status.state}，发送结束帧")
                            logger.info(f"📊 当前序列号: {sequence_number}, 已处理音频块数: {chunk_count}")
                            end_request = downlink_pb2.StreamAudioMessageRequest(
                                device_id=device_id,
                                user_id=user_id,
                                audio_data=b"",
                                sample_rate=16000,
                                channels=1,
                                bit_depth=16,
                                task_id=task_id,  # 使用相同的task_id
                                priority=downlink_pb2.PRIORITY_MEDIUM,
                                sequence_number=sequence_number,
                                is_end=True,
                                stream_session_id=stream_session_id
                            )
                            yield end_request
                            end_frame_sent = True
                            logger.info("✅ 结束帧已发送，TTS流处理完成")
                            break
                        elif status.state in ["error", "failed", "cancelled"]:
                            logger.error(f"❌ TTS处理失败，状态: {status.state}")
                            # 即使失败也要发送结束帧
                            end_request = downlink_pb2.StreamAudioMessageRequest(
                                device_id=device_id,
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
                            end_frame_sent = True
                            logger.info("✅ 结束帧已发送，TTS流处理失败")
                            break
                            
            except Exception as e:
                logger.error(f"❌ TTS流处理异常: {e}")
                # 即使发生异常，也要发送结束帧
                logger.info("🎯 异常情况下发送结束帧")
                end_request = downlink_pb2.StreamAudioMessageRequest(
                    device_id=device_id,
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
                end_frame_sent = True
                logger.info("✅ 异常情况下结束帧已发送")
                raise
            finally:
                # 确保在流结束时发送结束帧（如果还没有发送的话）
                if chunk_count > 0 and not end_frame_sent:
                    logger.warning("⚠️ 检测到音频流结束但未发送结束帧，强制发送")
                    logger.info(f"📊 强制发送详情: 序列号={sequence_number}, 音频块数={chunk_count}, 最后音频时间={time.time() - last_audio_time:.2f}秒前")
                    end_request = downlink_pb2.StreamAudioMessageRequest(
                        device_id=device_id,
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
                elif chunk_count > 0:
                    logger.info("🔍 检查流是否正常结束...")
                    # 这里可以添加额外的检查逻辑，确保结束帧被正确发送
        
        # 调用Downlink流式接口
        logger.info("📤 调用Downlink流式接口...")
        response = await downlink_stub.StreamAudioMessage(stream_generator())
        
        if response.success:
            logger.info(f"✅ 单个音频流测试成功: {response.message}")
            logger.info(f"📊 响应详情: success={response.success}, message='{response.message}'")
            return True
        else:
            logger.error(f"❌ 单个音频流测试失败: {response.error_message}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 测试异常: {e}")
        return False
    finally:
        # 关闭连接
        if 'tts_channel' in locals():
            await tts_channel.close()
        if 'downlink_channel' in locals():
            await downlink_channel.close()
        logger.info("🔌 连接已关闭")

if __name__ == "__main__":
    success = asyncio.run(test_single_audio_stream())
    if success:
        print("🎉 单个音频流测试成功！")
    else:
        print("💥 单个音频流测试失败！") 