---
name: nexus-app-builder
description: >-
  引导新建、修改、构建、部署与分发 PingCode 扩展应用：工作项面板、项目页、仪表盘部件、Wiki 内容块、
  事件处理、Webhook，以及 Custom UI / Native UI、Resolver、manifest、scope。适用于「新建应用」
  「脚手架 / nexus create」「加一块面板」「做个仪表盘部件」「Wiki 里嵌图表」「Resolver / manifest 是什么」
  「怎么部署 / 怎么分发 / 怎么发布到开发或预发」「nexus deploy / distribute」「构建验证 / build-web」等，
  即使用户未说 Nexus；按意图分支，不强制跑完创建→分发全链路。
  不要用于通用 PingCode 配置或脱离扩展应用的 REST 调用；现网白屏/部署失败/运行时故障用 nexus-app-debugger；
  「能不能发布 / 部署前检查」用 nexus-app-reviewer；安全审计/漏洞评估用 nexus-security-reviewer。
license: MIT
metadata:
  maintainer: pingcode
  namespace: nexus
  labels: nexus,builder,cli,custom-ui,native-ui
---

# Nexus App Builder

## 何时使用

- 新建或修改 Nexus 应用（脚手架 / `nexus create`、项目页、工作项面板、仪表盘、Wiki 块、事件、Webhook 等）
- Nexus 专属概念咨询（Resolver、Bridge、manifest、scope、外部域名）
- 构建验证与部署分发：`build-web`、`nexus deploy` / `distribute`，以及「怎么部署 / 怎么发布到开发或预发」
- 开发期编译/构建错误由本 skill 继续修；现网白屏、部署失败、运行时故障交 `nexus-app-debugger`

## 硬约束

1. 先判断意图：**咨询 / 新建 / 改已有 / 部署分发**——按需分支，**不强制**跑完创建→分发全链路。
2. **开始前打开并读完** [references/boundaries.md](references/boundaries.md) 与 [references/platform-invariants.md](references/platform-invariants.md)。
3. **新建**应用时始终用 `nexus create`（或本包 `scripts.create_nexus_app`）脚手架——禁止手搓无 `app.id` 的工程；纯咨询与改已有应用不要跑 create。
4. 绝不在对话中索要/接收 API 令牌；引导用户本机 `nexus login`。
5. 前端构建口径：裸 `nexus deploy` **不会**自动 `build-web`；本包 `deploy_nexus_app` 会尝试构建（无前端脚本则跳过）。裸 CLI 部署前有前端时 **ALWAYS** 先 `npm run build-web`。无 `nexus install`（分发后管理员安装）。
6. **知识原则**：按条件打开单个参考文件（见 [references/docs-online.md](references/docs-online.md)）；完整平台参考按需 `search_nexus_docs`，**不编造**、勿整目录预读。
7. 包前缀 `@pc-nexus/*`，CLI 为 `nexus`；文件名 `manifest.yaml`。
8. UI Invoke ~5s；长任务用异步队列。`display` 不是鉴权。

## 意图分支

先选一条主路径，再加载对应参考（**不强制**全链路）：

| 意图 | 路由 |
| --- | --- |
| 仅方案 / 概念咨询 | 读 [references/plan-only.md](references/plan-only.md)；停止于解释与示例 |
| 新建可部署应用 | 读 [references/create-new-app.md](references/create-new-app.md) |
| 改已有应用行为 | 读 [references/extend-existing-app.md](references/extend-existing-app.md) |
| 仅部署 / 分发 | 读 [references/deploy-only.md](references/deploy-only.md)；不大改功能 |
| 现网白屏 / 部署失败 / 运行时报错 | 交接 `nexus-app-debugger` |
| 发布前就绪审查 | 交接 `nexus-app-reviewer` |
| 深度安全审计 | 交接 `nexus-security-reviewer` |

开发中的普通编译/构建错误由本 skill 继续修；现网白屏、部署失败、复杂运行时故障交 `nexus-app-debugger`。

## 工作流细节

### 前置（仅当要跑 nexus / 脚手架 / 部署）

- Node ≥ 24；`npm install -g @pc-nexus/cli`；`nexus whoami --json` 验证登录。
- 多选项（模板、站点域名）让用户选；站点只传域名（如 `acme.pingcode.com`）。

### 新建（A）

模板（与 `scripts.create_nexus_app` / 官方 `nexus create` 一致）：

| 模板                                                           | 说明                                    |
| -------------------------------------------------------------- | --------------------------------------- |
| `react-custom-ui`                                              | **默认优先**；iframe Custom UI（React） |
| `angular-custom-ui` / `vue-custom-ui` / `javascript-custom-ui` | 其他 Custom UI                          |
| `react-native-ui` / `angular-native-ui`                        | Native UI（`Nx*` 宿主原生渲染）         |
| `event-typescript` / `webhook-typescript`                      | 事件 / Webhook，无前端                  |

选型：要完全自定义布局/第三方组件库 → Custom UI；要与产品视觉一致、用平台 `Nx*` 组件 → Native UI。二者渲染路径不同，NEVER 在 Custom UI 里当 Native 用 `@pc-nexus/react` 的 `Nx*`。

```bash
# 在本 skill 目录下
python3 -m scripts.create_nexus_app \
  --template react-custom-ui \
  --name <app-name> \
  --directory <parent-directory>
```

选 `target`：`references/list-nexus-extensions.md` + 官方扩展点文档；**逐字复制**。

### 定制（只打开当前任务需要的一份）

- Custom UI 最小路径：[references/ui-resolver-min-path.md](references/ui-resolver-min-path.md)
- Native UI 最小路径：[references/native-ui-min-path.md](references/native-ui-min-path.md)（manifest 连线见 [references/manifest-basics.md](references/manifest-basics.md)）
- 事件 / Webhook 最小路径：[references/event-webhook-min-path.md](references/event-webhook-min-path.md)
- 深读（**按章节跳读，一次只开一份**；勿因指南互链再通读其它长文）：
  - [references/nexus-custom-ui-developer-guide.md](references/nexus-custom-ui-developer-guide.md)
  - [references/nexus-backend-developer-guide.md](references/nexus-backend-developer-guide.md)
  - [references/nexus-app-manifest-guide.md](references/nexus-app-manifest-guide.md)
  - [references/nexus-development-guide.md](references/nexus-development-guide.md)（仅路径 A 或相关章节）

### 部署 / 分发（仅用户要求或任务明确需要）

见 [references/deploy-only.md](references/deploy-only.md)。优先本包脚本（agent 亲自跑，勿只甩命令）。`--distribute` 时必须传 `--site <域名>`。

### 在线检索

见 [references/docs-online.md](references/docs-online.md)。

## NEVER

- 把 display 当鉴权；对话中粘贴密钥
- 编造未核实的 target / scope / API（用本包 references + 官方在线文档）
- 抢走现网故障主路径（`nexus-app-debugger`）或默认做完整发布审查（`nexus-app-reviewer`）
- 宣称「已上线」但管理员尚未安装

## 交接

现网故障（白屏/部署失败/运行时）→ `nexus-app-debugger`；「能不能发布」→ `nexus-app-reviewer`；越权/租户/凭据 → `nexus-security-reviewer`。
