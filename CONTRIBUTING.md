# 贡献指南

感谢你对 LightWMS 项目的关注！我们欢迎任何形式的贡献。

## 如何贡献

### 报告 Bug

1. 在 [Issues](https://github.com/你的用户名/lightwms/issues) 中搜索是否已有相同问题
2. 如果没有，创建新的 Issue，包含：
   - 问题描述
   - 复现步骤
   - 期望行为
   - 实际行为
   - 环境信息（操作系统、浏览器、Docker 版本等）

### 提交功能建议

1. 在 Issues 中创建新的 Feature Request
2. 描述你想要的功能及其使用场景
3. 如果可能，提供实现思路

### 提交代码

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 开发环境设置

### 前置要求

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/你的用户名/lightwms.git
cd lightwms

# 后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# 前端（新终端）
cd frontend
npm install
npm run dev
```

## 代码规范

### Python (后端)

- 遵循 PEP 8 规范
- 使用有意义的变量名和函数名
- 添加必要的注释和文档字符串

### TypeScript (前端)

- 使用 ESLint 进行代码检查
- 组件使用 PascalCase 命名
- 函数和变量使用 camelCase 命名

## 提交信息规范

使用清晰的提交信息：

```
feat: 添加新功能
fix: 修复 bug
docs: 更新文档
style: 代码格式调整
refactor: 代码重构
test: 添加测试
chore: 构建/工具相关
```

## 行为准则

- 尊重所有贡献者
- 保持友善和专业的交流
- 接受建设性的批评

## 问题反馈

如有任何问题，请通过 Issues 联系我们。

再次感谢你的贡献！
