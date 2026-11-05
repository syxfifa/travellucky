# 验证记录

验证环境：Windows、Node 20.20.2、Python 3.11.5；日期 2026-11-05。

已通过：
- `npm ci` 安装前端依赖，`npm run build` 完成 Vue/TypeScript 检查及 Vite 生产构建。
- `python -m compileall -q backend/app`。
- `.venv/Scripts/python -m pytest backend/tests -q`：20 passed。
- `.venv/Scripts/python -m pip check`：No broken requirements found。
- FastAPI TestClient 完整 startup/shutdown，`/health`、`/`、`/account`、`/api/public/config.js` 返回 200。
- 新增测试覆盖管理接口鉴权、公开配置不返回服务端凭据、禁止设置页写密钥、POI坐标解析及无定位时不伪造路线。
- Compose 与 workflow YAML 可解析，目标平台 linux/amd64。
- 前端已移除 Google Maps SDK 依赖及加载逻辑，后端移除 Google 地图服务和调度分支。
- Python 直接依赖固定为本次安装验证的版本，前后端 Node 依赖使用 lockfile。

未验证：
- 此机器没有 Docker，未执行实际 docker build/docker run。CI 已加入非 root 启动和健康检查，尚未触发。
- 未提供模型、高德和小红书凭据，未进行真实行程生成或实际扫码登录。平台风控、Cookie续期及海外地点覆盖无法保证。
- 没有执行浏览器视觉回归或完整业务端到端回归；保留功能的源码已导入，但不能把离线测试当作全部业务验收。
- 没有配置远程地址、Actions Secrets 和 Git 作者身份；没有提交或推送到 GitHub/DockerHub。

已知非阻断警告：
- 上游 CSS 引用部分缺失图片/字体，构建会警告；可能影响使用这些旧样式的区域。
- 结果页 ECharts/导出组件造成较大 JS bundle，Vite 给出体积警告。
- `/api/public/config.js` 是有意保留的运行时脚本，不由 Vite 打包。
- 上游 Pydantic v2 兼容写法产生弃用警告，当前测试通过。

本地重跑：
```powershell
.venv/Scripts/python -m pytest backend/tests -q
npm --prefix frontend run build
```

容器及真实业务验收命令见 README.md；在有 Docker 和凭据的主机上执行后，补充验收结果。
