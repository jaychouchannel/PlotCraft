<p align="center">
  <img src="png/logo-banner.svg" width="100%" alt="PlotCraft — AI 驱动的科研论文矢量图生成器"/>
</p>

<div align="right">

[English](README.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md)

</div>

# PlotCraft

**AI 驱动的科研论文矢量图生成器 · 沙箱渲染 · 期刊就位**

> 用自然语言描述你要画的图，PlotCraft 调用大模型生成 matplotlib 代码，在后端隔离沙箱中执行，直接产出可投 Nature / Cell / Science 级别的 SVG 矢量图——所有密钥本地加密、所有代码本地运行、所有数据不出本机。

---

## 这是什么

<img src="png/5a48d1507b4c2021da7f255f5f191d5b.png" width="32%" alt="示例图1" />

科研绘图长期是论文写作里最磨人的环节：

- GraphPad / Origin 选项繁杂，鼠标点十几层菜单才出一张图；
- 手写 matplotlib 调参繁琐，配色、字体、统计标注、矢量导出每个都要查文档；
- AI 生图工具（GPT-4 / Gemini）能写代码但跑不起来，闭环只在聊天框里。

PlotCraft 把"自然语言 → 代码 → 渲染 → 矢量输出"这条链路一次性打通：

1. 你在 Web 界面里**用一句话描述要画的图**（"5 条曲线，x 是 0~10，y 是 sin 函数，标签 Time (s) / Amplitude"）；
2. 后端用你接入的大模型生成 matplotlib Python 代码；
3. 代码被丢进**隔离子进程沙箱**执行，强制 `Agg` 后端、断网、超时 60s、禁止 import `os / sys / socket / subprocess / requests / pathlib` 等危险模块；
4. 渲染出的 `output.svg` 直接回传到前端内联预览，可下载、可二次编辑代码后重新渲染；
5. 整个会话（prompt + 代码 + SVG）写入本地 SQLite 历史，可回溯、可清空。

**它不是另一个 ChatGPT 套壳**，而是把 LLM 生成代码后真正"跑出图来"这一步做扎实了的本地化工具。

---

## 仓库特点

### 🎯 矢量优先，期刊就位
- 直接渲染 SVG（`plt.savefig(format="svg", dpi=300, bbox_inches="tight")`），无损缩放，可直接嵌入 LaTeX / Word / InDesign；
- system prompt 注入 **Nature 风格配色**（`#E64B35 #4DBBD5 #00A087 #3C5488 #F39B7F #8491B4`）与排版规范：轴标签带单位、字体大小分档（轴 12pt / 刻度 10pt / 图例 10pt / 标题 14pt）、统计标注语义化（`*p<0.05`、`**p<0.01`、`***p<0.001`）；
- 内置 8 类科研图模板：折线（误差棒）、分组柱状（显著性）、散点+回归、箱线+小提琴、热图、雷达、双轴折线、Kaplan-Meier 生存曲线——覆盖生命科学 / 材料科学 / 临床医学最常见图型。

### 🔒 本地加密 · 密钥不出本机
- AI 厂商 API Key 用 **Fernet 对称加密**（`cryptography` 库）后写入本地 SQLite，密钥由 `ONE_ENCRYPT_KEY` 环境变量持有；
- 前端只展示脱敏后的 `api_key_masked`，明文密钥永不下发；
- 不上传任何第三方云，自托管部署时数据完全在用户机器上。

### 🏝 沙箱执行 · LLM 代码不越权
- 每次渲染开一个临时目录（`tempfile.mkdtemp`），脚本独立执行完即删；
- 环境变量层禁代理 (`NO_PROXY=*`)、强制 `MPLBACKEND=Agg`（不弹窗）；
- system prompt 硬性约束模型不得 import `os / sys / socket / requests / httpx / subprocess / shutil / pathlib / importlib`，不得读写 `output.svg` 之外的文件；
- 子进程超时 60s 自动 `kill`，防止死循环；
- 渲染失败时把 stderr 末尾 500 字回传前端，方便迭代修代码。

### 🔌 模型即插即用 · 多供应商统一接口
- 内置两个 provider：
  - `openai_compat`：兼容 OpenAI Chat Completions 协议（DeepSeek / 通义千问 / Moonshot / 智谱 / Together / OpenRouter / 本地 vLLM 等只要兼容 OpenAI 接口都可接）；
  - `gemini`：Google Gemini（`google-genai` SDK）；
- `replicate` 接口已预留，未来接入物理化位图生成模型；
- 模型可在「模型」页 UI 里随时增删改，base_url / model_name / api_key / extra 字段全部表单化配置，无需改代码。

### 📝 模板系统 · 内置可继承，自定义可编辑
- 内置 8 张图型模板带 `system_prompt` + `user_template` 占位符（如 `{xlabel}`、`{series}`），启动时自动播种到 SQLite；
- 内置模板只读（避免被误改），可"另存为"再编辑成自己的版本；
- 模板支持 category 分类、前端按类别下拉筛选；
- 用户提示词编辑框接收模板内容后可继续编辑，模板只是起点不是天花板。

### 🖥 现代前端 · 代码可改可重渲染
- React 19 + TypeScript 7 + Vite 8 + Tailwind 4；
- 内嵌 **CodeMirror**（VSCode Dark 主题 + Python 语法高亮），生成的代码可在线编辑；
- "重新渲染"按钮把改过的代码 POST 回 `/api/generate/render`，不消耗 LLM 配额；
- SVG 用 `dangerouslySetInnerHTML` 内联预览（沙箱已断网，SVG 仅本地路径），右键保存即可；
- 下载按钮：`.svg` 矢量、`.py` 源码一键取走。

### 🗂 历史回放 · 不丢任何一次实验
- 每次生成（成功 / 失败 / 仅代码）都进 `generations` 表，含 `model_id` / `template_id` / `user_input` / `generated_code` / `output_svg` / `status` / `error` / `created_at`；
- 「历史」页可查最近 50 条、单条删除、全清空；
- 失败记录也保留，方便对照排查环境问题。

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI · Pydantic · aiosqlite · aiofiles · cryptography · openai · google-genai |
| 渲染 | matplotlib（Agg 后端）· numpy · pandas · scipy（按需） |
| 前端 | React 19 · TypeScript 7 · Vite 8 · Tailwind 4 · @uiw/react-codemirror · react-router-dom 7 |
| 存储 | SQLite（模型配置 / 模板 / 历史） |
| 沙箱 | tempfile + subprocess + Agg + 断网 + 超时 kill |

---

## 项目结构

```
PlotCraft/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI 入口，CORS + lifespan + 模板播种
│   │   ├── config.py            环境变量加载
│   │   ├── crypto.py            Fernet 加解密
│   │   ├── db.py                aiosqlite 连接 + 表初始化
│   │   ├── executor.py          沙箱执行（核心安全边界）
│   │   ├── prompts.py           科研绘图 system prompt 模板
│   │   ├── models.py            Pydantic 数据模型
│   │   ├── providers/
│   │   │   ├── base.py          Provider 抽象基类
│   │   │   ├── factory.py       provider 工厂
│   │   │   ├── openai_compat.py OpenAI 兼容协议
│   │   │   └── gemini.py        Google Gemini
│   │   └── routes/
│   │       ├── generate.py       /api/generate + /api/generate/render
│   │       ├── history.py        历史记录 CRUD
│   │       ├── models.py         模型配置 CRUD
│   │       └── templates.py      模板 CRUD + 启动播种
│   ├── templates_seed/           8 个内置图型 JSON
│   │   ├── 01_line_with_errorbar.json
│   │   ├── 02_grouped_bar_significance.json
│   │   ├── 03_scatter_regression.json
│   │   ├── 04_box_violin.json
│   │   ├── 05_heatmap.json
│   │   ├── 06_radar.json
│   │   ├── 07_dual_axis_line.json
│   │   └── 08_kaplan_meier.json
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx              路由 + 导航
│   │   ├── main.tsx             入口
│   │   ├── index.css            Tailwind
│   │   ├── lib/api.ts           前端 API 客户端
│   │   ├── components/
│   │   │   └── SetupBanner.tsx  未配置密钥时引导
│   │   └── pages/
│   │       ├── Generate.tsx     生成主界面（核心）
│   │       ├── History.tsx      历史
│   │       ├── ModelConfig.tsx  模型配置
│   │       └── Templates.tsx    模板管理
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
└── .gitignore
```

---

## 快速开始

### 1. 后端

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

# 生成 Fernet 密钥
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 把密钥写入 .env
cp .env.example .env
# 编辑 .env，把上面输出的密钥填到 ONE_ENCRYPT_KEY=
# 同时可改 HOST / PORT / DB_PATH

# 启动
uvicorn app.main:app --reload --port 8000
```

启动后访问 `http://127.0.0.1:8000/docs` 看 OpenAPI 文档。

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

打开浏览器访问终端提示的 Vite 地址（默认 `http://localhost:5173`）。

### 3. 配置模型

进入「模型」页，添加一个模型：

- **OpenAI 兼容协议**（DeepSeek 示例）
  - `provider`: `openai_compat`
  - `base_url`: `https://api.deepseek.com/v1`
  - `model_name`: `deepseek-chat`
  - `api_key`: 你的 DeepSeek key
- **Gemini**
  - `provider`: `gemini`
  - `model_name`: `gemini-2.5-flash`
  - `api_key`: Google AI Studio key
- **本地 vLLM / Ollama（OpenAI 兼容）**
  - `base_url`: `http://localhost:8000/v1`（vLLM）或 `http://localhost:11434/v1`（Ollama）
  - `api_key`: 本地服务可填任意非空字符串

### 4. 生成第一张图

1. 进「生成」页，选模型 + 选模板（例如「散点 + 线性回归」）；
2. 模板 prompt 自动填入编辑框，按你的数据改写：
   ```
   请绘制一张散点 + 线性回归图：
   - x: 细胞直径 (μm)，y: 蛋白表达量 (RFU)
   - 30 个样本，散点带噪声
   - 拟合直线 + 95% 置信区间阴影
   - 图内显示 R² 和 p 值
   - Nature 风格配色
   ```
3. 点「生成」 → 几秒后右侧出 SVG 预览；
4. 满意 → 下载 `.svg` / `.py`；不满意 → 在 CodeMirror 里改代码 →「重新渲染」不消耗 LLM 配额。

---

## 效果演示

下面三张图全部由 PlotCraft 生成——自然语言输入，LLM 生成 matplotlib 代码，后端沙箱执行渲染，导出 SVG（此处为 GitHub 预览重新栅格化）。

<p align="center">
  <img src="png/808aa00d130c44832a83f8700828c46e.png" width="32%" alt="示例图2" />
  <img src="png/5564f828049e55775e89289333cddf9b.png" width="32%" alt="示例图3" />
</p>
<p align="center"><em>左：多系列折线 + 误差棒 · 中：分组柱状 + 显著性标注 · 右：散点 + 线性回归 + 95% 置信区间</em></p>

---

## 内置模板清单

| # | 类别 | 模板名 | 典型场景 |
|---|---|---|---|
| 01 | 折线 | 折线图（多系列+误差棒） | 时序响应、剂量-效应曲线 |
| 02 | 柱状 | 分组柱状图（显著性） | 多处理组比较 + ANOVA 显著性标注 |
| 03 | 散点 | 散点 + 线性回归 | 相关性分析、R² / p 值标注 |
| 04 | 分布 | 箱线 + 小提琴 | 组间分布对比、批次效应检查 |
| 05 | 热图 | 热图 | 基因表达、混淆矩阵 |
| 06 | 雷达 | 雷达图 | 多维评分对比 |
| 07 | 双轴 | 双轴折线 | 不同量纲同图（如温度 vs 产率） |
| 08 | 生存 | Kaplan-Meier | 生存分析 + log-rank 检验 |

---

## 安全模型

| 风险 | 缓解措施 |
|---|---|
| LLM 生成恶意代码读取本地文件 | system prompt 禁用 `os/sys/pathlib/subprocess/open()` 等 import；执行子进程无 `~` 访问隔离的临时目录 |
| LLM 调用公网外泄数据 | system prompt 禁用 `socket/requests/httpx`；env 设 `NO_PROXY=*`；下游依赖可进一步用网络命名空间隔离 |
| 死循环 / 死锁耗尽 CPU | 子进程 60s 超时自动 `kill` |
| API Key 泄露 | Fernet 对称加密入库；前端只接脱敏字符串 |
| SVG XSS | SVG 内联渲染仅在前端 DOM，沙箱断网，不执行外部资源加载 |

> ⚠️ **生产部署提示**：本仓库 CORS 默认 `allow_origins=["*"]`，适合本地单人使用。多用户/公网部署请改为白名单前端域名，并加上认证层。

---

## 适用与不适用

**适合**
- 个人科研工作者 / 研究生 / 博后快速出论文配图
- 实验室内部共享绘图工具（自托管在组内服务器）
- 教学：让学生观察 LLM 如何把自然语言映射成可执行 matplotlib 代码

**不适合**
- 需要严格合规审计的企业级多人协作（无认证 / 审计日志）
- 替代专业出版工具（Adobe Illustrator 仍可对 SVG 做最后微调）
- 处理需要交互式 3D / 大数据 WebGL 渲染的图（沙箱只跑 matplotlib）

---

## 路线图

- [ ] PDF / EPS 导出（目前仅 SVG）
- [ ] 批量生成（一次 prompt 多张子图拼 panel）
- [ ] 复制图型参数到新数据（"换数据不换风格"）
- [ ] Replicate / FAL 物理化位图 provider 接入
- [ ] 用户态 sandpack-js 在浏览器侧预渲染，省 Python 子进程开销

---

## 许可证

本仓库当前未声明开源许可证。在添加 LICENSE 文件之前，默认适用作者保留全部版权的隐式条款——可参考使用，但二次分发 / 衍生 / 商用前请联系作者授权。

---

## 致谢

- 配色灵感：[ggsci - Nature 期刊配色](https://github.com/nanxstats/ggsci)
- 模板思路：matplotlib gallery + 论文图惯例
- 沙箱思路：Jupyter `%%script` / `nbconvert` isolate 模式
