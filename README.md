# travellucky

基于 [TripStar](https://github.com/1sdv/TripStar) 改造，上游基线 `2455e6f66ab9bf1a45147aca7103117a7a1600f9`。保留 LICENSE（GPL-2.0）和上游署名。

Vue 3 + TypeScript + FastAPI + HelloAgents。保留 AI 行程、多城市、预算、天气、酒店、历史、导出、知识图谱、伴游问答、多语言及偏好记忆；地图只使用高德。原有高德 HTTP 服务的空结果占位实现已替换为真实 REST 请求和解析。

## 1. 结构

```text
frontend/                       Vue 页面、高德地图、行程及设置
backend/app/agents/             行程规划工作流
backend/app/services/           LLM、高德、小红书数据服务
backend/app/api/routes/account* 小红书专用浏览器登录管理
backend/app/memory/             偏好记忆
backend/tests/                  回归测试
Dockerfile                      前端、签名依赖、Python依赖、运行四阶段
.dockerignore                   排除密钥、依赖、Git和运行数据
.env.example                    无真实密钥的环境变量模板
docker-compose.yml              本地/PVE/NAS部署
.github/workflows/docker.yml    DockerHub自动发布
```

## 2. 配置和安全边界

复制 `.env.example` 为 `.env` 并填写：

| 变量 | 用途 |
| --- | --- |
| LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_ID | 兼容 OpenAI 格式的模型服务 |
| VITE_AMAP_WEB_KEY | 高德 Web 服务 Key，仅后端使用 |
| VITE_AMAP_WEB_JS_KEY | 高德 JS API Key |
| VITE_AMAP_SECURITY_JS_CODE | 高德 JS 安全配置 |
| XHS_COOKIE | 可选，已有登录态的环境变量导入 |
| ADMIN_TOKEN | 自行生成高强度随机字符串，保护小红书管理接口 |
| BIND_IP / APP_PORT | 默认 127.0.0.1:7860 |
| MEMORY_USE_SQLITE | 默认模板启用 SQLite 持久化 |
| DOCKERHUB_USERNAME / IMAGE_TAG | 拉取或构建镜像名称与版本 |

所有部署凭据从环境变量读取；没有 secret ARG、镜像内 .env 或运行时密钥 JSON。前端地图配置通过运行时接口提供，同一镜像可用于不同部署。浏览器 SDK 必然能看见其 JS Key 和 JS 安全配置，应设置高德域名白名单；它们不是后端服务密钥。LLM Key、后端高德 Key 和 Cookie 不通过该接口返回。

设置页只读；改 `.env` 后执行 `docker compose up -d --force-recreate`，单纯 restart 不会重新读取环境变量。不要公开 `.env`、docker inspect 输出或包含 Cookie 的请求。

当前适用于个人/可信内网部署，旅行 API、历史和匿名偏好不具有多用户账号隔离。默认只监听本机；开放到公网前必须在反向代理增加 HTTPS 和全站身份认证（包括 WebSocket），不能仅依赖 ADMIN_TOKEN。

## 3. 小红书登录

1. 配置 ADMIN_TOKEN 后打开 `/account`，输入管理令牌。
2. 点击“登录”，在专用浏览器画面点击小红书登录入口，使用手机扫码；需要输入时先点击输入框，再从文字栏输入。
3. 点击刷新查看最新画面，完成平台要求的验证。系统每 30 秒读取该浏览器会话的 Cookie，并更新服务进程环境和内存配置。
4. 点击“检测可用性”实际发起一次搜索。`cookie_synced_unverified` 仅表示已同步，`available` 才表示最近一次检测通过。
5. 失效或风控时由用户重新登录/验证；不保证永久续期。网络异常与账号验证状态分别显示。
6. 退出清除当前进程会话。由于严格禁止将凭据落盘，重启容器后需重新登录，或通过 XHS_COOKIE 注入已有 Cookie。若 .env 中仍配置旧 Cookie，重启会再次加载它，应一并清空。

浏览器使用临时配置，不持久化登录目录；截图仅在经鉴权的响应中返回，不写文件。一次部署共用一个小红书会话。为了避免不同进程会话不一致，保持一个 Uvicorn worker。某些验证码或平台风控可能不适合远程画面操作，此时使用浏览器手动登录后通过 XHS_COOKIE 环境变量导入。

## 4. 本地构建与 docker run 验证

安装 Docker Engine/Desktop（Linux 容器模式），在项目根目录执行。PowerShell 复制命令：

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

将随机输出填入 ADMIN_TOKEN，并填写模型和高德配置；Linux 使用 `cp .env.example .env`。

```sh
docker build --platform linux/amd64 -t travellucky:local .
docker volume create travellucky-data
docker run -d --name travellucky --init --platform linux/amd64 --env-file .env -e TZ=Asia/Shanghai --shm-size=256m --cap-drop=ALL --security-opt=no-new-privileges:true -p 127.0.0.1:7860:7860 -v travellucky-data:/app/backend/data travellucky:local
docker logs --tail 100 travellucky
docker exec travellucky id
docker exec travellucky python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:7860/health').read().decode())"
docker inspect --format '{{.State.Health.Status}}' travellucky
```

访问 http://localhost:7860 。预期容器 UID/GID 为 10001，健康检查为 healthy。完整业务验收：配置密钥→登录并检测小红书→生成单城市行程→多城市→检查地图、预算、图片、天气、历史、导出、问答及偏好记忆。无密钥仍可启动，但不代表业务接口可用。

Compose 本地构建：

```sh
docker compose up -d --build
docker compose logs --tail 100
docker compose ps
```

发布后的 PVE/NAS 部署：复制 `docker-compose.yml`、`.env.example` 为 `.env`，填 DockerHub 用户名和 IMAGE_TAG。已有镜像不需要源码：

```sh
docker compose pull
docker compose up -d --no-build
```

PVE 建议在 x86_64 Debian/Ubuntu 虚拟机内安装 Docker。绿联 NAS 用 Docker/Compose 项目导入；需要局域网访问时将 BIND_IP 设置成 NAS 的局域网 IP 或 0.0.0.0。镜像仅 amd64，不提供 ARM 原生支持。默认命名卷可避免 NAS 绑定目录权限问题；若改成宿主目录，需由管理员提前创建并赋予 UID/GID 10001 写权限。数据库、历史、图片缓存位于 `/app/backend/data`，备份此卷即可；Cookie 不在卷内。

## 5. Git 初始化、提交和推送

当前目录已初始化为 main；无需再次初始化。下面是从零开始也可使用的完整 PowerShell 命令（替换身份及 GitHub 用户名）。先在 GitHub 创建空的 `travellucky` 仓库，不勾选 README/LICENSE/gitignore。

```powershell
Set-Location C:\Users\Administrator\Desktop\travlelucky
git init -b main
git config user.name "YOUR_NAME"
git config user.email "YOUR_EMAIL"
git add .
git diff --cached --stat
git commit -m "feat: initialize travellucky with amap and docker deployment"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/travellucky.git
git push -u origin main
```

如果 origin 已存在，使用 `git remote set-url origin ...`。Windows 若提示 dubious ownership，仅在确认目录属于自己的项目时执行 `git config --global --add safe.directory C:/Users/Administrator/Desktop/travlelucky`。本地目录沿用原有拼写 travlelucky，项目及镜像名为 travellucky。

## 6. DockerHub、Actions Secrets 和版本发布

1. 登录 DockerHub，进入 Repositories → Create repository，名称填写 `travellucky`，选择你的个人命名空间与可见性。镜像路径必须是小写 `用户名/travellucky`。
2. Docker 账户设置 → Personal access tokens → Generate new token，填写名称（例如 github-travellucky）、有效期，选择 **Read & Write** 权限；无需 Delete。创建后保存令牌，页面通常只显示一次。详细说明：https://docs.docker.com/security/access-tokens/
3. GitHub 仓库 → Settings → Secrets and variables → Actions → New repository secret，新增：
   - `DOCKERHUB_USERNAME`：DockerHub 用户名（不是邮箱）。
   - `DOCKERHUB_TOKEN`：上一步 Access Token。
4. 应用 LLM、高德和小红书凭据只放部署主机环境；不需要加入 Actions Secrets，CI 不接触它们。

工作流监听 main push、v 开头 tag 和 workflow_dispatch；Buildx 仅构建 linux/amd64，登录 DockerHub 后推送。GitHub Actions 缓存通过 `type=gha` 读写；Dockerfile 还使用依赖缓存挂载。

| 触发 | 镜像标签 |
| --- | --- |
| main push 或选择 main 手动执行 | latest、sha-短提交号 |
| v1.0.0 | 1.0.0、sha-短提交号 |
| v1.1.0-rc.1 | 1.1.0-rc.1、sha-短提交号 |
| 其他分支手动执行 | sha-短提交号 |

版本 tag 不覆盖 latest。非版本格式的 v 标签会被校验拒绝。发布命令：

```sh
git add .
git commit -m "feat: prepare 1.0.0 release"
git push origin main
git tag -a v1.0.0 -m "release: travellucky 1.0.0"
git push origin v1.0.0
```

若没有新变更，跳过提交步骤。生产部署建议 IMAGE_TAG=1.0.0 或 sha-xxxxxxx，更新时执行 pull 和 up -d --no-build。不要移动已经发布的 tag。

## 7. 常见踩坑

- DockerHub denied：检查仓库命名空间、用户名、Token 的 Read & Write 权限、有效期及 GitHub Secrets 名称。
- exec format error：宿主不是 amd64；本项目没有 ARM 镜像，模拟运行不保证性能。
- NAS Permission denied：绑定目录 UID/GID 错误，优先使用命名卷；不要用 root 运行服务来掩盖权限问题。
- 镜像泄密：不要添加凭据 ARG/ENV 默认值、不要复制 .env 或会话文件。构建缓存同样不能包含凭据。`.dockerignore` 排除 Git、依赖、数据和日志；如果曾误提交密钥，必须轮换。
- latest 未变化：版本 tag 不更新 latest；本地也不会自动拉取最新镜像，执行 compose pull 后再 up。
- 前端地图空白：检查 JS Key 类型、域名白名单、安全配置；Web 服务 Key 与 JS Key 不可混用。运行时配置无需重新构建镜像。
- Cookie 存在但抓取失败：可能过期、风控、网络或接口变化，必须实际检测；自动同步不等于自动续期。
- 多 worker：登录态和后台任务在内存中，必须保持单 worker。
- 仅健康检查通过：不等于外部 API 可用；需使用真实凭据执行业务验收。
- 镜像较大：Chromium 是扫码浏览器所需，Python Agent 依赖也较多；首次拉取需要时间。
- 许可证：本项目基于 GPL-2.0 上游，保留 LICENSE 和来源；分发时同时提供对应源码。

## 8. 本次验证记录

见 VALIDATION.md。没有执行远程推送或 DockerHub 发布；需要用户配置仓库地址和 Actions Secrets。登录、模型及高德真实联网验证需要实际凭据。
