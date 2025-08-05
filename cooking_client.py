import grpc
import json
import time
import uuid

# 导入生成的gRPC代码
import cooking_pb2 as cooking_pb2
import cooking_pb2_grpc as cooking_pb2_grpc

class CookingClient:
    """做菜咨询客户端"""
    
    def __init__(self, host='localhost', port=50052):
        self.channel = grpc.insecure_channel(f'{host}:{port}')
        self.stub = cooking_pb2_grpc.CookingAdvisorStub(self.channel)
        self.conversation_history = []
        self.extracted_data = {}
        # 生成稳定的用户ID
        self.user_id = f"user_{uuid.uuid4().hex[:8]}"
    
    def get_cooking_advice(self, query, start=0):
        """获取做菜建议"""
        try:
            # 构建请求
            request = cooking_pb2.CookingRequest(
                user_id=self.user_id,  # 添加用户ID
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
                
                yield response.phase_response, response.extracted_info, response.status
                
        except grpc.RpcError as e:
            print(f"gRPC流式调用错误: {e}")
            yield None, None, f"error: {e}"
    
    def close(self):
        """关闭连接"""
        self.channel.close()

def main():
    """主函数 - 演示客户端使用"""
    client = CookingClient()
    
    print("=== 做菜咨询系统 ===")
    print("输入 'quit' 退出")
    print()
    
    try:
        # 第一轮咨询
        query = input("请告诉我你想做什么菜或者需要什么帮助？\n> ")
        if query.lower() == 'quit':
            return
        
        print("\n正在获取建议...")
        response, extracted_info, status = client.get_cooking_advice(query, start=1)
        
        if status == "success":
            print(f"\nAI回复: {response}")
            print(f"提取信息: {extracted_info}")
        else:
            print(f"错误: {status}")
        
        # 多轮对话
        while True:
            print("\n" + "="*50)
            query = input("请继续告诉我更多信息，或者输入 'quit' 退出\n> ")
            
            if query.lower() == 'quit':
                break
            
            print("\n正在获取建议...")
            response, extracted_info, status = client.get_cooking_advice(query, start=0)
            
            if status == "success":
                print(f"\nAI回复: {response}")
                print(f"提取信息: {extracted_info}")
            else:
                print(f"错误: {status}")
    
    except KeyboardInterrupt:
        print("\n\n程序被中断")
    finally:
        client.close()
        print("连接已关闭")

if __name__ == '__main__':
    main() 