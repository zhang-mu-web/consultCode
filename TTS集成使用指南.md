# TTS和Downlink服务集成使用指南

## 概述

本指南介绍如何将TTS（文本转语音）和Downlink（音频播放）服务集成到烹饪咨询系统中，为AI回复提供语音播放功能。

## 服务架构

```
烹饪咨询系统
    ↓
TTS服务 (192.168.2.109:50051)
    ↓ (文本转语音)
音频数据
    ↓
Downlink服务 (192.168.2.88:50055)
    ↓ (音频播放)
设备播放
```

## 文件结构

```
cooking/
├── tts/                          # TTS服务相关文件
│   ├── downlink.proto           # Downlink服务协议定义
│   ├── downlink_pb2.py          # 生成的Downlink客户端代码
│   ├── downlink_pb2_grpc.py     # 生成的Downlink服务代码
│   ├── tts_service_pb2.py       # 生成的TTS客户端代码
│   ├── tts_service_pb2_grpc.py  # 生成的TTS服务代码
│   └── tts_downlink_manager.py  # 原始TTS管理器
├── tts_integration.py           # TTS集成管理器
├── tts_config.json              # TTS配置文件
├── test_tts_integration.py      # TTS集成测试脚本
└── cooking_client.py            # 集成了TTS的烹饪客户端
```

## 功能特性

### 1. 语音合成
- **简单模式**: 直接合成完整文本并播放
- **流式模式**: 实时合成和播放，支持长文本
- **多语音支持**: 可配置不同的语音ID和语言

### 2. 音频播放
- **实时播放**: 支持流式音频播放
- **任务管理**: 支持取消正在播放的任务
- **优先级控制**: 支持设置音频播放优先级

### 3. 集成功能
- **自动播放**: AI回复自动转换为语音播放
- **手动控制**: 支持手动启用/禁用TTS功能
- **状态管理**: 完整的连接状态和任务状态管理

## 使用方法

### 1. 基本使用

```python
from cooking_client import CookingClient

# 创建客户端，启用TTS功能
client = CookingClient(enable_tts=True)

# 获取烹饪建议（会自动播放语音）
response, extracted_info, status = client.get_cooking_advice("蛋炒饭怎么做")
```

### 2. 控制TTS功能

```python
# 启用TTS功能
client.enable_tts_feature(True)

# 禁用TTS功能
client.enable_tts_feature(False)

# 停止当前语音播放
client.stop_current_speech()
```

### 3. 直接使用TTS管理器

```python
from tts_integration import CookingTTSManager, TTSMode
import asyncio

async def test_tts():
    # 创建TTS管理器
    manager = CookingTTSManager()
    
    # 连接服务
    await manager.connect()
    
    # 播放语音
    success = await manager.speak_text("你好，我是烹饪助手！", TTSMode.SIMPLE)
    
    # 断开连接
    await manager.disconnect()

# 运行
asyncio.run(test_tts())
```

### 4. 交互式使用

运行集成了TTS的客户端：

```bash
python cooking_client.py
```

支持的命令：
- `quit`: 退出程序
- `stop`: 停止当前语音播放
- `tts on`: 启用TTS功能
- `tts off`: 禁用TTS功能

## 配置说明

### 1. 服务端点配置

在 `tts_config.json` 中配置服务端点：

```json
{
  "tts_service": {
    "endpoint": "192.168.2.109:50051"
  },
  "downlink_service": {
    "endpoint": "192.168.2.88:50055"
  }
}
```

### 2. 音频参数配置

```json
{
  "audio_params": {
    "sample_rate": 16000,
    "channels": 1,
    "bit_depth": 16
  }
}
```

### 3. 语音参数配置

```json
{
  "voice_params": {
    "default_voice_id": "1",
    "default_language": "zh",
    "device_type": "cooking"
  }
}
```

## 测试

### 1. 运行集成测试

```bash
python test_tts_integration.py
```

测试内容包括：
- TTS服务连接测试
- 简单TTS模式测试
- 流式TTS模式测试
- 烹饪建议TTS测试
- 任务取消功能测试
- 语音参数设置测试

### 2. 测试烹饪客户端

```bash
python cooking_client.py
```

然后输入烹饪相关问题，观察：
- 文本回复是否正确
- 语音是否自动播放
- 语音质量是否良好

## 故障排除

### 1. 连接问题

**问题**: TTS服务连接失败
**解决方案**:
- 检查服务端点是否正确
- 确认TTS和Downlink服务是否运行
- 检查网络连接

### 2. 语音播放问题

**问题**: 语音不播放
**解决方案**:
- 检查TTS功能是否启用
- 确认音频设备是否正常
- 查看日志中的错误信息

### 3. 性能问题

**问题**: 语音播放延迟
**解决方案**:
- 使用流式模式减少延迟
- 检查网络带宽
- 优化音频参数

## 高级功能

### 1. 自定义语音参数

```python
manager = CookingTTSManager()
manager.set_voice_params(voice_id="2", language="zh")
```

### 2. 获取统计信息

```python
stats = manager.get_stats()
print(f"TTS调用次数: {stats['tts_calls']}")
print(f"音频块发送数: {stats['audio_chunks_sent']}")
print(f"总音频字节数: {stats['total_pcm_bytes']}")
```

### 3. 健康检查

```python
# 自动健康检查（连接时）
await manager.connect()

# 手动健康检查
await manager._health_check()
```

## 注意事项

1. **服务依赖**: 确保TTS和Downlink服务正常运行
2. **网络要求**: 需要稳定的网络连接
3. **资源管理**: 及时断开连接释放资源
4. **错误处理**: 妥善处理连接和播放异常
5. **性能考虑**: 长文本建议使用流式模式

## 扩展功能

### 1. 多语言支持
可以扩展支持多种语言的TTS：

```python
manager.set_voice_params(language="en")  # 英语
manager.set_voice_params(language="ja")  # 日语
```

### 2. 语音识别集成
可以结合语音识别实现完整的语音交互：

```python
# 语音输入 + TTS输出
voice_input = speech_to_text()
response = get_cooking_advice(voice_input)
text_to_speech(response)
```

### 3. 个性化语音
可以根据用户偏好设置不同的语音：

```python
# 根据用户设置选择语音
user_voice = get_user_voice_preference(user_id)
manager.set_voice_params(voice_id=user_voice)
```

## 总结

通过TTS和Downlink服务的集成，烹饪咨询系统现在具备了完整的语音交互能力：

- ✅ 文本转语音功能
- ✅ 实时音频播放
- ✅ 流式处理支持
- ✅ 任务管理功能
- ✅ 配置化管理
- ✅ 完整的测试覆盖

这大大提升了用户体验，使烹饪指导更加直观和便捷！ 