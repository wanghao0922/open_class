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
- 当前苯环修饰仅提供甲氧基，可选邻、间、对位；酯化试剂为甲醇和2-乙基己醇。当前共12种可探索结构（含未修饰肉桂酸），甲醇酯化生成甲酯。
- 原有40种分子素材保留用于查看历史答案，补充4种甲酯后，素材目录共44种。已移除的选项不能用于新提交；修改旧草稿时会保留仍可用的修饰，其余修饰恢复为未取代或未酯化状态。
- 新增甲酯图复用原有AI图的柔化色彩纹理，原子、化学键和氢原子数量根据甲酯的分子连接重新生成；未发送新的图片API请求，溯源记录包含纹理来源。
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

## 公网入口与本地存储

当前公网版使用 `backend.gateway:app`：Render 提供页面和图片，授课电脑主动通过 WSS 连接公网服务，所有课堂 API 请求在本机执行，数据保存至 `data/classroom.db`。不需要开放本机入站端口，也不依赖 Render PostgreSQL。

- 上课前双击 `开启公网课堂.cmd`，保持电脑开机、联网、不休眠。
- 下课后双击 `关闭公网课堂.cmd`。关闭连接不会删除课堂记录。
- 首次连接可能需要等待免费网页服务唤醒。断线会自动重连；发送中的操作若提示失败，应重试并核对统计。
- 本机连接配置位于 `data/relay-config.json`，其中的随机密钥必须与 Render 的 `LOCAL_RELAY_TOKEN` 一致，不提交Git。
- 网页和图片由 Render 提供；首页图片使用 WebP，统计图片按需加载，不在登录前下载40张分子图片。

## Render 部署配置

仓库根目录新增Blueprint时选择 `sunscreen_classroom/render.yaml`；若手动创建Web Service，Root Directory设为 `sunscreen_classroom`。

Blueprint 创建独立的免费 Web Service。配置 `LOCAL_RELAY_TOKEN` 后，启动本机连接即可。免费服务空闲后会休眠，课前提前访问唤醒。

- Build Command：`pip install -r requirements.txt && cd frontend && npm ci && npm run build`
- Start Command：`uvicorn backend.gateway:app --host 0.0.0.0 --port $PORT --workers 1`
- Health Check：`/healthz`，同时显示本机是否连接。
- 设置随机的 `LOCAL_RELAY_TOKEN`，与本机配置一致。教师账号和密码从本机配置读取。
- 不配置图片API密钥，课堂无需在线生成图片。图片、结构和前端依赖均由应用本身提供，无公共CDN依赖。
- Render 不保存课堂数据库；所有正式记录以授课电脑的 `data/classroom.db` 为准。停用连接后可备份 `data` 文件夹。
- 如需恢复完全云端存储，可将服务启动模块改回 `backend.app:app`，并配置外部PostgreSQL的 `DATABASE_URL`、教师密码和安全Cookie。不要将 SQLite 数据库直接放到免费Render文件系统上充当持久化存储。

Render官方文档：https://render.com/docs/deploy-fastapi ，https://render.com/docs/free 。
