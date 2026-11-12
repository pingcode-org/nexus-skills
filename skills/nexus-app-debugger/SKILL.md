---
name: nexus-app-debugger
description: >-
  诊断并修复 PingCode 扩展应用故障：工作项面板、项目页、仪表盘、Wiki 内容块、事件或 Webhook 异常，
  即使用户未说 Nexus。适用于报错、崩溃、白屏、部署失败、安装后不显示、权限不足、Resolver 异常、
  Custom UI 不渲染、日志缺失、外部 API 被拦截、UI Invoke 超时、事件/Webhook 不触发，
  或 nexus logs / deploy / lint / serve 相关故障。
  不要用于从零新建应用（nexus-app-builder）、发布就绪检查（nexus-app-reviewer）或深度安全审计（nexus-security-reviewer）。
license: MIT
metadata:
  maintainer: pingcode
  namespace: nexus
  labels: nexus,debugger,troubleshooting
---

# Nexus App Debugger

## 何时使用

用户以**排查已有故障**为目标——即使未说 “Nexus”，只要描述扩展面板、项目页、工作项面板、Wiki 块、仪表盘、事件或 Webhook 异常即可。

## 执行授权

直接运行诊断与修复命令（`nexus lint`、`logs`、`deploy` 等）。不要把本可自行执行的命令只交给用户。  
例外：`nexus login`、`nexus serve` 需用户交互式终端。

## MUST

1. **证据优先**；对照 `references/debug-playbook.md`，**定位根因即停**（多独立缺陷则先部署后运行时）。
2. **开始前打开并读完** [references/boundaries.md](references/boundaries.md) 与 [references/platform-invariants.md](references/platform-invariants.md)。
3. 低成本先跑：`node -v`、`nexus --version`、`nexus lint`，再读源码/日志。
4. 修复后**复验**同一证据路径；清理临时 DEBUG 日志。
5. **知识原则**：排障打开 [references/debug-playbook.md](references/debug-playbook.md)；字段/API 明细按条件检索（[references/docs-online.md](references/docs-online.md)），勿整目录预读。
6. 不索要 token；引导本机 `nexus login`。

## NEVER

- 证据不足时断言唯一根因
- 编造未核实的平台字段 / API 行为
- 把「加功能 / 从零创建」当调试主路径（转 `nexus-app-builder`）
- 用完整安全审计替代故障定位；带 `--no-verify` 发布

## 工作流

1. 分类：部署失败 / 运行时 / 可见性（安装后看不到）——见 playbook 路由表。
2. Lint →（Custom UI）检查 `web/main/dist` 与 `build-web` → deploy 状态 → `nexus logs -e <dev-env>`（默认名常为 `development`；自定义 Development 类型名也可用）。
3. 白屏看浏览器 DevTools（前端日志不进 `nexus logs`）。
4. 需要热重载：用户本机 `nexus serve -e <dev-env>`（`-f` 限定函数；`--debug` 挂 9229）。
5. 仅生产 / Staging 问题：开发者中心或企业日志；CLI `logs` / `serve` **仅 Development 类型**。
6. 匹配 playbook「常见错误速查」后直接修复并复验。

## 关键核对

- Invoke 名 ↔ `resolver.define`；`resolver.function` ↔ `functions[].key`；handler `<file>.<export>`
- 403：scopes + 重新 distribute/安装；外部 API：`permissions.external.fetch.*`
- UI Invoke 5s；事件名逐字；HMR 时 `nexus.json` resource key/port

## 交接

知识咨询或新需求 → `nexus-app-builder`；发布检查 → `nexus-app-reviewer`；系统性 AuthZ/租户 → `nexus-security-reviewer`。
