#!/usr/bin/env python3
"""
做菜咨询gRPC服务器
提供智能做菜指导服务
"""

import grpc
import json
import requests
import jinja2
import os
from concurrent import futures
from user_manager import get_user_manager
import cooking_pb2
import cooking_pb2_grpc

# 火山引擎豆包API配置
ARK_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

# 从环境变量或配置文件获取API密钥
def get_ark_api_key():
    """获取API密钥"""
    # 优先从环境变量获取
    api_key = os.environ.get("ARK_API_KEY")
    if api_key:
        return api_key
    
    # 从配置文件获取
    try:
        with open('cooking_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            return config.get('ark_api_key', '')
    except:
        return ''

ARK_API_KEY = get_ark_api_key()

# 移除咨询阶段相关逻辑

def build_dynamic_prompt(conversation_history, extracted_data, start, user_id=None):
    """构建动态提示词"""
    # 读取提示词模板
    with open('cooking_prompt.txt', 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # 构建对话历史文本
    history_text = ""
    for item in conversation_history:
        history_text += f"{item['content']}\n"
    
    # 构建提取信息文本
    extracted_info = ""
    if extracted_data:
        for key, value in extracted_data.items():
            if key != '回复':
                extracted_info += f"{key}: {value}\n"
    
    # 添加用户上下文信息
    user_context = ""
    if user_id:
        user_manager = get_user_manager()
        user_context_data = user_manager.get_user_context_for_prompt(user_id)
        
        if user_context_data:
            user_context = "### 用户上下文信息:\n"
            if user_context_data.get("current_dish"):
                user_context += f"- 当前菜品: {user_context_data['current_dish']}\n"
            if user_context_data.get("taste_preferences"):
                user_context += f"- 口味偏好: {', '.join(user_context_data['taste_preferences'])}\n"
            if user_context_data.get("cooking_level"):
                user_context += f"- 烹饪水平: {user_context_data['cooking_level']}\n"
            if user_context_data.get("allergies"):
                user_context += f"- 过敏原: {', '.join(user_context_data['allergies'])}\n"

    # 渲染模板
    template = jinja2.Template(template_content)
    
    return template.render(
        start=start,
        all_information_key=[],
        current_phase=None,
        current_phase_name="",
        phase_questions="",
        conversation_history=history_text,
        extracted_info=extracted_info,
        user_context=user_context
    )

def call_ark_api(prompt, query):
    """调用火山引擎豆包API"""
    try:
        # 加载AI配置
        with open('cooking_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        ai_config = config['ai_config']
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ARK_API_KEY}"
        }
        
        data = {
            "model": ai_config['model'],
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": query}
            ],
            "max_tokens": ai_config['max_tokens'],
            "temperature": ai_config['temperature'],
            "stream": ai_config['stream']
        }
        
        response = requests.post(ARK_ENDPOINT, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                return content
            else:
                print(f"API响应格式错误: {result}")
                return get_fallback_response(query)
        else:
            print(f"API调用失败，状态码: {response.status_code}, 响应: {response.text}")
            return get_fallback_response(query)
            
    except Exception as e:
        print(f"API调用异常: {e}")
        return get_fallback_response(query)

def get_fallback_response(query):
    """获取备用响应（当API调用失败时）"""
    try:
        # 加载配置文件中的备用响应
        with open('cooking_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        fallback_responses = config['fallback_responses']
        
        # 检查是否有匹配的备用响应
        for key, response in fallback_responses.items():
            if key in query:
                return json.dumps(response)
        
        # 返回默认响应
        return json.dumps(fallback_responses['default'])
        
    except Exception as e:
        print(f"加载备用响应失败: {e}")
        # 返回简单的备用响应
        return json.dumps({
            "阶段性回复": "好的，我来帮你规划做菜方案。请告诉我你想做什么菜或者有什么食材？",
            "食材准备": "用户询问做菜建议"
        })

class CookingAdvisorServicer(cooking_pb2_grpc.CookingAdvisorServicer):
    """做菜咨询服务实现"""
    
    def GetCookingAdvice(self, request, context):
        """获取做菜建议"""
        try:
            # 获取用户ID - 直接使用请求中的user_id字段
            user_id = request.user_id
            
            # 获取用户管理器
            user_manager = get_user_manager()
            
            # 确保用户存在
            if not user_manager.get_user(user_id):
                user_manager.create_user(user_id)
                print(f"创建新用户: {user_id}")
            
            # 转换对话历史格式
            conversation_history = []
            for item in request.conversation_history:
                conversation_history.append({
                    "role": item.role,
                    "content": item.content
                })
            
            # 转换提取数据格式
            extracted_data = dict(request.extracted_data)
            
            # 简单提取菜品信息并更新用户状态
            print(f"处理用户输入: {request.query}")
            dish_name = user_manager.extract_dish_from_text(request.query)
            if dish_name:
                user_manager.set_current_dish(user_id, dish_name)
                print(f"识别菜品: {dish_name}")
            
            # 构建动态提示（包含用户上下文）
            dynamic_prompt = build_dynamic_prompt(
                conversation_history, 
                extracted_data, 
                request.start,
                user_id
            )
            
            # 获取AI响应
            ai_response = call_ark_api(dynamic_prompt, request.query)
            
            # 解析响应
            try:
                response_data = json.loads(ai_response)
                reply = response_data.get('回复', '')
                
                # 检查是否是完成菜品的状态
                current_state = response_data.get('当前状态', '')
                if current_state == '结束关怀':
                    # 用户完成了一道菜，更新状态
                    # 尝试从对话历史中提取菜品名称
                    completed_dish = ""
                    if conversation_history:
                        # 从最近的对话中寻找菜品名称
                        for item in reversed(conversation_history[-5:]):  # 检查最近5条对话
                            if item['role'] == 'user':
                                dish_name = user_manager.extract_dish_from_text(item['content'])
                                if dish_name:
                                    completed_dish = dish_name
                                    break
                    
                    user_manager.complete_dish(user_id, completed_dish)
                
                # 提取其他信息
                extracted_info = {}
                for key, value in response_data.items():
                    if key != '回复':
                        extracted_info[key] = value
                
                # 打印用户统计信息
                self._print_user_stats(user_id)
                
                return cooking_pb2.CookingResponse(
                    phase_response=reply,
                    extracted_info=extracted_info,
                    status="success"
                )
                
            except json.JSONDecodeError:
                return cooking_pb2.CookingResponse(
                    phase_response=ai_response,
                    status="error: invalid json response"
                )
                
        except Exception as e:
            print(f"服务错误: {e}")
            return cooking_pb2.CookingResponse(
                phase_response=f"服务错误: {str(e)}",
                status="error"
            )
    

    
    def _print_user_stats(self, user_id: str):
        """打印用户统计信息"""
        try:
            user_manager = get_user_manager()
            user_data = user_manager.get_user(user_id)
            
            if user_data:
                print(f"\n=== 用户 {user_id} 统计信息 ===")
                print(f"烹饪水平: {user_data['profile']['cooking_level']}")
                print(f"口味偏好: {user_data['profile']['preferences']['taste']}")
                print(f"过敏原: {user_data['profile']['allergies']}")
                print(f"已学会的菜品: {user_data.get('learned_dishes', [])}")
                print(f"当前正在做的菜: {user_data['current_session']['dish']}")
                print("=" * 40)
        except Exception as e:
            print(f"打印用户统计信息失败: {e}")

def serve():
    """启动gRPC服务器"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    cooking_pb2_grpc.add_CookingAdvisorServicer_to_server(
        # 创建一个 CookingAdvisorServicer 的实例，并将其添加到 grpc 服务器中
        CookingAdvisorServicer(), server
    )
    
    # 监听端口
    server.add_insecure_port('[::]:50052')
    server.start()
    print("做菜咨询gRPC服务器已启动，监听端口 50052")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("服务器正在关闭...")
        server.stop(0)

if __name__ == '__main__':
    serve() 