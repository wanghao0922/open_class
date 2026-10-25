# 探秘防晒霜的主要成分 · AI赋能互动课堂

独立的 React + TypeScript + FastAPI 应用。现有 float_bubble、gravity_bubble 程序和作答文件不参与本应用运行。

## 本地使用

Windows PowerShell，在本目录运行：

```powershell
.\setup-local.ps1
.\start-local.ps1
```

已安装环境时直接运行 `start-local.ps1`，默认端口8010。

- 学生入口：`http://127.0.0.1:8010/`
- 教师入口：`http://127.0.0.1:8010/teacher`
- 教师账号与随机密码：`data/local-credentials.json`（第一次初始化创建，文件不进Git）。也可以从 `.env.example` 复制为 `.env`，自行设置账号密码。
- 仅停止本应用：`stop-local.ps1`。不要用“结束全部Python进程”等命令。
- 同一Wi-Fi演示：`start-local.ps1 -Lan`，使用教师电脑的局域网IPv4地址访问；若Windows防火墙询问，请只在可信课堂网络按需放行。二维码弹窗内可填写可访问的地址。

同一浏览器的标签页共享登录身份。教师和模拟学生请使用不同浏览器、无痕窗口或独立浏览器会话。

## 教师课前流程

1. 教师登录，点击“创建正式课堂”，填写课程名称和全班小组总数（默认10）。已有小组加入后总数锁定，避免统计分母变化。
2. 点击“邀请加入”，投影二维码或复制学生链接。学生输入小组号及汇报人姓名；同组再次加入使用同一汇报人姓名。更名由教师在“各组作答”中完成。
3. 环节一在课堂完成。进入环节二，点击“开放本任务”。学生提交至少两条不同猜想后看到实时匿名统计。
4. 切换环节三并开放任务，环节二自动结束。修饰提交后，教师查看结构归并结果；环节二、三均可重新开放。
5. “各组作答”可查看汇报人、答案和版本；点击统计卡片查看对应小组。CSV导出最新答案，JSON包含提交历史。
6. 点击“创建独立演示课堂”生成10组示例数据，含8/10组（80%）案例。演示课堂会明显标注，不混入正式课堂。

学生已填写草稿保存在该浏览器本地。提交失败会提示重试，未收到成功响应时不会宣称提交成功。若另一设备已更新本组答案，服务端拒绝旧版本覆盖，刷新后再核对提交。请勿在共用设备上随意切换同组身份。

## 官能团与分子

- 七个猜想框支持鼠标/触屏拖拽，也支持“点选卡片—点击目标”。同一官能团可以重复加入表达数量；同一组合的排列顺序不影响归并。
- 环节二不判化学正误，不根据氧原子数提前排除猜想。每框最多12个官能团以保持可操作性，至少两条不同组合方可提交。
- 苯环相对侧链只取邻、间、对三类；最多一个甲基/甲氧基/氨基，以及一次乙醇/正己醇/2-乙基己醇酯化，共40种结构（含未修饰肉桂酸）。
- 结构SVG由RDKit根据SMILES校验生成，均保留反式烯键；酯化后连接的是烷氧基，不是把完整醇原样挂上去。目标结构为对甲氧基肉桂酸-2-乙基己酯，C18H26O3。
- 电子云素材通过用户指定的自定义图片API请求制作，模型请求名gpt-image-2，原始尺寸1536×1024。逐图发现AI绘制的部分键和支链不可靠，因此交付图保留AI图的柔化云层色彩纹理，球棍前景由已校验的分子连接与氢原子数量重新绘制，最终尺寸仍为1536×1024；热点直接来自校正后的原子坐标。原始图归档在 `work/ai-originals`，溯源记录在 `frontend/public/molecules/asset-provenance.json`。这属于AI素材与化学校正模型组合的教学插图，不是量子化学电子密度/静电势图。无伪造吸收峰、能级和评分。
- 酯化不能直接等同于延长π共轭链；目标产物主要是UVB吸收剂，不能描述为全面覆盖UVA。教学来源：梁素艳等《基于“结构决定性质”大概念下的素养教学——探究防晒霜的有效成分》，化学教育，2024，45(1)，DOI:10.13884/j.1003-3807hxjy.2022110109；UVB定位依据：https://pubmed.ncbi.nlm.nih.gov/31112187/ 。

## 开发与验证

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests -q
```

前端开发：`cd frontend; npm run dev`，将API代理到8010端口。前端正式构建：`npm run build`。结构目录重新生成：`scripts/make_catalog.py`（需RDKit）；图片生成日志保存在Git忽略的 `work` 目录，已有尝试不会自动重试。原始图片不应在未核对的情况下重新覆盖。

应用数据保存在 `data/classroom.db`，停止应用后备份整个 `data` 文件夹即可。素材目录 `frontend/public/molecules` 应随代码发布。用户配置、课堂数据库、日志及图片API密钥不进Git。

## Render 部署准备

仓库根目录新增Blueprint时选择 `sunscreen_classroom/render.yaml`；若手动创建Web Service，Root Directory设为 `sunscreen_classroom`。

Blueprint 会创建独立的免费 Web Service 和 PostgreSQL 数据库，自动将数据库连接地址注入 `DATABASE_URL`，部署时填写教师密码即可。免费数据库会在创建后30天到期；到期前导出课堂记录或迁移到长期数据库。免费服务空闲后会休眠，课前提前访问唤醒。

- Build Command：`pip install -r requirements.txt && cd frontend && npm ci && npm run build`
- Start Command：`uvicorn backend.app:app --host 0.0.0.0 --port $PORT --workers 1`
- Health Check：`/api/health`
- 设置 `TEACHER_USERNAME`、自定义 `TEACHER_PASSWORD`、`COOKIE_SECURE=true`、外部PostgreSQL的 `DATABASE_URL`。
- 不配置图片API密钥，课堂无需在线生成图片。图片、结构和前端依赖均由应用本身提供，无公共CDN依赖。
- 免费Web Service重启/休眠会丢失本地写入数据，因此正式公网课堂必须提供外部数据库；不能将SQLite作为Render持久存储。免费实例有冷启动，课前提前打开并完整演练。本交付不代表已完成公网部署。
- 不应把已有SQLite文件直接当成PostgreSQL使用。上线先创建空数据库和新课堂；如需迁移历史，使用JSON导出保留档案，后续按需迁移。

Render官方文档：https://render.com/docs/deploy-fastapi ，https://render.com/docs/free 。
