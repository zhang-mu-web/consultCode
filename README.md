# 做菜咨询gRPC系统

这是一个基于gRPC的做菜咨询指导系统，参考了法律咨询程序的结构，提供专业的做菜指导服务。

## 功能特点

- **智能对话**: 基于火山引擎豆包API的自然语言交互
- **详细指导**: 提供非常详细的步骤指导，包括火候、时间、动作等
- **食材管理**: 分组列举食材，避免信息过载
- **记忆功能**: 严格跟踪已确认的食材，避免重复询问
- **需求一致**: 严格保持用户最初需求，不得偏离
- **替代方案**: 为缺少的食材提供合适的替代方案
- **安全提示**: 在指导过程中适时加入安全提示
- **配置化**: 支持外部配置文件管理prompt和系统参数
- **用户属性管理**: 动态提取和更新用户属性（烹饪水平、口味偏好、过敏原等）
- **Redis持久化**: 用户数据24小时持久化存储
- **实时统计**: 多用户统计分析和监控
- **个性化推荐**: 基于用户属性的个性化建议
- **用餐人数管理**: 根据用餐人数智能调整食材分量
- **优化数据结构**: 精简冗余字段，提高存储效率和一致性

## 系统架构

```
cooking.proto          # gRPC服务定义
cooking_server.py      # 服务端实现（集成用户管理）
cooking_client.py      # 客户端实现
user_manager.py        # 用户属性管理系统（已优化）
migrate_data.py        # 数据迁移脚本
cooking_prompt.txt     # AI提示模板
cooking_config.json    # 系统配置文件
requirements.txt       # 依赖包
```

## 数据结构优化

### 优化前的问题
- **冗余字段**: `ingredient_inventory` 等存储相同信息
- **无意义字段**: `profile.name`、`cooking_history` 等在烹饪指导中无实际价值
- **过度设计**: `cooking_steps`、`current_step` 等字段增加复杂性但使用价值低
- **存储浪费**: 约40%的字段是冗余或无意义的

### 优化后的结构
```json
{
  "user_id": "用户唯一标识",
  "created_at": "创建时间",
  "last_active": "最后活跃时间",
  "profile": {
    "cooking_level": "烹饪水平",
    "preferences": {
      "taste": ["口味偏好"]
    },
    "allergies": ["过敏原"]
  },
  "current_session": {
    "dish": "当前菜品"
  }
}
```

### 优化效果
- **减少存储空间**: 删除约40%的冗余字段
- **提高一致性**: 避免多字段存储相同信息
- **简化维护**: 减少数据同步的复杂性
- **提升性能**: 减少Redis存储和传输开销
- **降低风险**: 减少隐私数据存储

## 安装依赖

```bash
pip install -r requirements.txt
```

## 生成gRPC代码

```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. cooking.proto
```

## 使用方法

### 1. 安装Redis

```bash
# Windows
# 下载并安装Redis for Windows

# Linux
sudo apt install redis-server
sudo systemctl start redis-server

# macOS
brew install redis
brew services start redis
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 数据迁移（可选）

如果之前有用户数据，建议运行数据迁移脚本：

```bash
python migrate_data.py
```

### 4. 启动服务器

```bash
python cooking_server.py
```

### 5. 运行客户端

```bash
python cooking_client.py
```

## 用户属性管理

系统动态提取和更新用户属性：

### 核心属性
- **烹饪水平**: beginner（新手）、intermediate（一般）、advanced（熟练）
- **口味偏好**: sweet（甜）、savory（咸）、spicy（辣）、sour（酸）、umami（鲜）
- **过敏原**: 花生、海鲜、鸡蛋、牛奶、坚果、大豆、小麦等
- **厨具设备**: 炒锅、蒸锅、烤箱、微波炉、电饭煲等
- **用餐人数**: 1-5人，影响食材分量计算

### 会话信息
- **当前菜品**: 正在指导的菜品名称
- **已确认食材**: 用户确认的食材状态（有/没有）
- **缺少食材**: 自动从已确认食材推导得出

## 示例对话

```
用户: 我想学做番茄炒蛋
AI: 番茄炒蛋是一道经典的家常菜，简单易学！我来帮你准备详细的步骤。

用户: 我是新手，第一次做菜
AI: 好的！新手的话我们从最基础的开始。家里有鸡蛋和番茄吗？

用户: 有鸡蛋，没有番茄
AI: 没关系！可以用其他蔬菜代替。有洋葱或青椒吗？

用户: 有洋葱和青椒
AI: 太好了！现在需要调味料：盐、油、生抽，家里都有吗？

用户: 有盐和油，没有生抽
AI: 没问题！可以用酱油代替。现在开始做菜，第一步：把鸡蛋打散...
```

## 用户属性统计示例

```
=== 用户属性统计仪表板 ===
📊 总用户数: 15
🟢 活跃用户: 8
📈 活跃率: 53.3%

👨‍🍳 烹饪水平分布:
  beginner: 8 人 (53.3%)
  intermediate: 5 人 (33.3%)
  advanced: 2 人 (13.3%)

🍽️ 热门口味偏好:
  spicy: 12 人
  savory: 10 人
  sweet: 8 人

⚠️ 常见过敏原:
  花生: 3 人
  海鲜: 2 人

🔧 常用厨具:
  炒锅: 15 人
  电饭煲: 12 人
  烤箱: 5 人
```

## 技术栈

- **gRPC**: 高性能RPC框架
- **Protocol Buffers**: 数据序列化
- **Jinja2**: 模板引擎
- **Python**: 主要开发语言
- **火山引擎豆包API**: 真实AI服务
- **Redis**: 用户数据持久化
- **正则表达式**: 信息提取和模式匹配

## 扩展功能

- ✅ 集成真实的AI API（火山引擎豆包API）
- ✅ 用户属性动态提取和管理
- ✅ Redis数据持久化
- ✅ 多用户统计和监控
- ✅ 个性化推荐系统
- 添加数据库存储对话历史
- 支持多语言
- 添加图片识别食材功能
- 集成菜谱数据库

## 注意事项

- 确保服务器在客户端之前启动
- 默认端口为50051
- ✅ 已集成火山引擎豆包API，提供真实AI服务
- 需要网络连接以访问AI API 