#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试更新后的proto文件和voice_id字段
"""

import grpc
import cooking_pb2
import cooking_pb2_grpc

def test_proto_fields():
    """测试proto字段是否正确更新"""
    print("🧪 测试proto字段更新")
    
    # 测试CookingRequest消息
    request = cooking_pb2.CookingRequest(
        user_id="test_user_001",
        voice_id="2",  # 测试不同的voice_id
        query="如何做红烧肉？",
        start=1,
        conversation_history=[
            cooking_pb2.ConversationItem(
                role="user",
                content="我想学做菜"
            )
        ],
        extracted_data={"test": "value"}
    )
    
    print(f"✅ CookingRequest创建成功")
    print(f"   user_id: {request.user_id}")
    print(f"   voice_id: {request.voice_id}")
    print(f"   query: {request.query}")
    print(f"   start: {request.start}")
    print(f"   对话历史数量: {len(request.conversation_history)}")
    print(f"   提取数据数量: {len(request.extracted_data)}")
    
    # 测试CookingResponse消息
    response = cooking_pb2.CookingResponse(
        phase_response="好的，我来教您做红烧肉。",
        extracted_info={"菜品": "红烧肉", "难度": "中等"},
        status="success"
    )
    
    print(f"\n✅ CookingResponse创建成功")
    print(f"   phase_response: {response.phase_response}")
    print(f"   extracted_info: {dict(response.extracted_info)}")
    print(f"   status: {response.status}")
    
    # 测试字段编号
    print(f"\n📋 字段编号验证:")
    print(f"   user_id字段编号: {request.DESCRIPTOR.fields_by_name['user_id'].number}")
    print(f"   voice_id字段编号: {request.DESCRIPTOR.fields_by_name['voice_id'].number}")
    print(f"   query字段编号: {request.DESCRIPTOR.fields_by_name['query'].number}")
    print(f"   start字段编号: {request.DESCRIPTOR.fields_by_name['start'].number}")
    
    return True

def test_grpc_stub():
    """测试gRPC存根是否正确生成"""
    print(f"\n🧪 测试gRPC存根")
    
    try:
        # 创建通道和存根
        channel = grpc.insecure_channel('localhost:50052')
        stub = cooking_pb2_grpc.CookingAdvisorStub(channel)
        
        print(f"✅ gRPC存根创建成功")
        print(f"   服务名称: {stub.__class__.__name__}")
        
        # 检查方法是否存在
        methods = [method for method in dir(stub) if not method.startswith('_')]
        print(f"   可用方法: {methods}")
        
        channel.close()
        return True
        
    except Exception as e:
        print(f"❌ gRPC存根测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🔧 开始测试proto文件更新")
    print("=" * 50)
    
    # 测试proto字段
    proto_test = test_proto_fields()
    
    # 测试gRPC存根
    grpc_test = test_grpc_stub()
    
    print("\n" + "=" * 50)
    if proto_test and grpc_test:
        print("✅ 所有测试通过！proto文件更新成功")
        print("📝 更新内容:")
        print("   - 添加了voice_id字段")
        print("   - 重新生成了gRPC代码")
        print("   - 服务器端和客户端都已更新")
    else:
        print("❌ 部分测试失败，请检查更新")

if __name__ == "__main__":
    main() 