import json
import os
import grpc
from concurrent import futures
import jinja2
import requests

# 导入生成的gRPC代码
import cooking_pb2
import cooking_pb2_grpc

# 导入用户管理系统
from user_manager import get_user_manager
from info_extractor import get_info_extractor

# 火山引擎豆包API配置
ARK_API_KEY = "0c0d41dc-5c1a-4c25-b5be-012b8e01c153"
ARK_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
os.environ["ARK_API_KEY"] = ARK_API_KEY
ARK_BASE_URL = 'https://ark.cn-beijing.volces.com/api/v3'

# 移除咨询阶段相关逻辑

def build_dynamic_prompt(conversation_history, extracted_data, start, user_id=None):
    """构建动态提示"""
    # 加载配置文件
    with open('cooking_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 加载prompt模板
    with open('cooking_prompt.txt', 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    # 准备对话历史
    history_text = "\n".join([
        f"[{item['role']} {i + 1}]: {item['content']}"
        for i, item in enumerate(conversation_history[-6:])
    ])
    
    # 整理已获取的信息
    extracted_info = ''
    for i, k in enumerate(list(extracted_data.keys())):
        extracted_info += f'信息{i+1}:' + k + ':' + extracted_data[k] + '\n'
    
    # 添加用户上下文信息
    user_context = ""
    if user_id:
        user_manager = get_user_manager()
        info_extractor = get_info_extractor()
        user_context_data = info_extractor.get_user_context_for_prompt(user_id)
        
        if user_context_data:
            user_context = "### 用户上下文信息:\n"
            if user_context_data.get("current_dish"):
                user_context += f"- 当前菜品: {user_context_data['current_dish']}\n"
            if user_context_data.get("confirmed_ingredients"):
                user_context += f"- 已确认食材: {json.dumps(user_context_data['confirmed_ingredients'], ensure_ascii=False)}\n"
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
            # 获取或创建用户ID（从请求中提取或生成）
            user_id = self._get_user_id_from_request(request)
            
            # 获取用户管理器
            user_manager = get_user_manager()
            info_extractor = get_info_extractor()
            
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
            
            # 从用户输入中提取信息并更新用户属性
            print(f"处理用户输入: {request.query}")
            extracted_info = info_extractor.extract_all_info(request.query, user_id)
            
            # 打印提取的信息
            if extracted_info["ingredients"]:
                print(f"提取的食材: {extracted_info['ingredients']}")
            if extracted_info["taste_preferences"]:
                print(f"提取的口味: {extracted_info['taste_preferences']}")
            if extracted_info["cooking_level"]:
                print(f"提取的烹饪水平: {extracted_info['cooking_level']}")
            if extracted_info["equipment"]:
                print(f"提取的厨具: {extracted_info['equipment']}")
            if extracted_info["allergies"]:
                print(f"提取的过敏原: {extracted_info['allergies']}")
            
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
    
    def _get_user_id_from_request(self, request) -> str:
        """从请求中获取用户ID"""
        # 方法1: 从查询中提取用户ID
        if request.query and len(request.query) > 10:
            # 简单的用户ID提取逻辑
            words = request.query.split()
            for word in words:
                if len(word) > 8 and word.isalnum():
                    return word
        
        # 方法2: 从对话历史中提取
        for item in request.conversation_history:
            if "用户ID" in item.content:
                # 提取用户ID的逻辑
                pass
        
        # 方法3: 生成默认用户ID
        import hashlib
        user_hash = hashlib.md5(request.query.encode()).hexdigest()[:8]
        return f"user_{user_hash}"
    
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
                print(f"厨具: {user_data['profile']['kitchen_equipment']}")
                print(f"用餐人数: {user_data['profile']['family_size']}")
                print(f"当前菜品: {user_data['current_session']['dish']}")
                print(f"已确认食材: {user_data['current_session']['confirmed_ingredients']}")
                print(f"食材库存: {len(user_data['ingredient_inventory'])} 种")
                print("=" * 40)
        except Exception as e:
            print(f"打印用户统计信息失败: {e}")

def serve():
    """启动gRPC服务器"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    cooking_pb2_grpc.add_CookingAdvisorServicer_to_server(
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