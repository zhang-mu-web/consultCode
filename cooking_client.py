import grpc
import json
import time
import uuid
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 导入生成的gRPC代码
import cooking_pb2 as cooking_pb2
import cooking_pb2_grpc as cooking_pb2_grpc

# TTS功能已移至服务器端，客户端不再需要TTS集成

class CookingClient:
    """做菜咨询客户端"""
    
    def __init__(self, host='localhost', port=50052, user_id=None, enable_tts=True):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = cooking_pb2_grpc.CookingAdvisorStub(self.channel)
        self.conversation_history = []
        self.extracted_data = {}
        
        # TTS功能开关（仅用于显示状态，实际TTS在服务器端处理）
        self.enable_tts = enable_tts
        
        # 用户ID管理：优先使用传入的user_id，其次从环境变量读取，最后生成新的
        if user_id:
            self.user_id = 537971611258480000
        else:
            # 尝试从环境变量读取用户ID
            env_user_id = os.getenv('COOKING_USER_ID')
            if env_user_id:
                self.user_id = env_user_id
            else:
                # 尝试从配置文件读取
                config_user_id = self._load_user_id_from_config()
                if config_user_id:
                    self.user_id = config_user_id
                else:
                    # 生成新的用户ID并保存到配置文件
                    self.user_id = f"user_{uuid.uuid4().hex[:8]}"
                    self._save_user_id_to_config(self.user_id)
        
        print(f"使用用户ID: {self.user_id}")
        if self.enable_tts:
            print("🎤 TTS语音功能已启用（服务器端处理）")
        else:
            print("🔇 TTS语音功能已禁用")
    
    def _load_user_id_from_config(self):
        """从配置文件加载用户ID"""
        try:
            if os.path.exists('user_config.json'):
                with open('user_config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('user_id')
        except Exception as e:
            print(f"读取配置文件失败: {e}")
        return None
    
    def _save_user_id_to_config(self, user_id):
        """保存用户ID到配置文件"""
        try:
            config = {'user_id': user_id}
            with open('user_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            print(f"用户ID已保存到配置文件: {user_id}")
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get_user_id(self):
        """获取当前用户ID"""
        return self.user_id
    
    def set_user_id(self, user_id):
        """设置新的用户ID"""
        self.user_id = user_id
        self._save_user_id_to_config(user_id)
        print(f"用户ID已更新为: {user_id}")
    
    def reset_conversation(self):
        """重置对话历史"""
        self.conversation_history = []
        self.extracted_data = {}
        print("对话历史已重置")
    
    def enable_tts_feature(self, enable=True):
        """启用或禁用TTS功能（仅客户端状态，实际TTS在服务器端处理）"""
        self.enable_tts = enable
        status = "启用" if enable else "禁用"
        print(f"🎤 TTS语音功能已{status}（服务器端处理）")
    
    def _speak_text_async(self, text: str):
        """异步播放语音（已移至服务器端处理）"""
        # TTS功能已在服务器端处理，客户端不再需要处理
        print("🎤 语音播放在服务器端处理中...")
    
    def _speak_text_sync(self, text: str):
        """同步播放语音（已移至服务器端处理）"""
        # TTS功能已在服务器端处理，客户端不再需要处理
        print("🎤 语音播放在服务器端处理中...")
    
    def get_cooking_advice(self, query, start=0):
        """获取做菜建议"""
        try:
            # 构建请求
            request = cooking_pb2.CookingRequest(
                user_id=self.user_id,  # 添加用户ID
                voice_id="1",  # 默认语音ID
                query=query,
                start=start,
                conversation_history=[
                    cooking_pb2.ConversationItem(
                        role=item['role'],
                        content=item['content']
                    ) for item in self.conversation_history
                ],
                extracted_data=self.extracted_data
            )
            
            # 调用gRPC服务
            response = self.stub.GetCookingAdvice(request)
            
            # 更新对话历史
            self.conversation_history.append({"role": "user", "content": query})
            self.conversation_history.append({"role": "assistant", "content": response.phase_response})
            
            # 更新提取的数据
            for key, value in response.extracted_info.items():
                self.extracted_data[key] = value
            
            # 语音播放在服务器端处理，客户端只需显示状态
            if self.enable_tts and response.phase_response:
                print("🎤 服务器端正在处理语音播报...")
            
            return response.phase_response, response.extracted_info, response.status
            
        except grpc.RpcError as e:
            print(f"gRPC调用错误: {e}")
            return None, None, f"error: {e}"
    
    def get_cooking_advice_stream(self, query, start=0):
        """流式获取做菜建议"""
        try:
            # 构建请求
            request = cooking_pb2.CookingRequest(
                user_id=self.user_id,  # 添加用户ID
                voice_id="1",  # 默认语音ID
                query=query,
                start=start,
                conversation_history=[
                    cooking_pb2.ConversationItem(
                        role=item['role'],
                        content=item['content']
                    ) for item in self.conversation_history
                ],
                extracted_data=self.extracted_data
            )
            
            # 调用gRPC流式服务
            responses = self.stub.GetCookingAdviceStream(request)
            
            for response in responses:
                # 更新对话历史
                self.conversation_history.append({"role": "user", "content": query})
                self.conversation_history.append({"role": "assistant", "content": response.phase_response})
                
                # 更新提取的数据
                for key, value in response.extracted_info.items():
                    self.extracted_data[key] = value
                
                # 语音播放在服务器端处理，客户端只需显示状态
                if self.enable_tts and response.phase_response:
                    print("🎤 服务器端正在处理语音播报...")
                
                yield response.phase_response, response.extracted_info, response.status
                
        except grpc.RpcError as e:
            print(f"gRPC流式调用错误: {e}")
            yield None, None, f"error: {e}"
    
    def stop_current_speech(self):
        """停止当前语音播放（服务器端处理）"""
        if self.enable_tts:
            print("🔇 语音播放停止功能由服务器端处理")
        else:
            print("🔇 TTS功能已禁用")
    
    def close(self):
        """关闭连接"""
        self.channel.close()

def main():
    """主函数 - 演示客户端使用"""
    # 创建客户端，启用TTS功能
    client = CookingClient(enable_tts=True)
    
    print("=== 做菜咨询系统 (带语音功能) ===")
    print("输入 'quit' 退出")
    print("输入 'stop' 停止当前语音播放")
    print("输入 'tts on/off' 启用/禁用TTS功能")
    print()
    
    try:
        while True:
            # 获取用户输入
            query = input("请告诉我你想做什么菜或者需要什么帮助？\n> ").strip()
            
            if query.lower() == 'quit':
                print("再见！")
                break
            elif query.lower() == 'stop':
                client.stop_current_speech()
                continue
            elif query.lower() == 'tts on':
                client.enable_tts_feature(True)
                continue
            elif query.lower() == 'tts off':
                client.enable_tts_feature(False)
                continue
            elif not query:
                continue
            
            print("\n正在获取建议...\n")
            
            # 获取建议
            response, extracted_info, status = client.get_cooking_advice(query)
            
            if response:
                print(f"AI回复: {response}")
                if extracted_info:
                    print(f"提取信息: {extracted_info}")
                print("\n" + "="*50)
            else:
                print(f"获取建议失败: {status}")
                print("\n" + "="*50)
    
    except KeyboardInterrupt:
        print("\n\n程序被中断，正在退出...")
    finally:
        client.close()

if __name__ == "__main__":
    main() 