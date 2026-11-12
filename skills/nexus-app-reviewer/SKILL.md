---
name: nexus-app-reviewer
description: >-
  对 PingCode Nexus 应用执行轻量级发布前就绪审查，覆盖 manifest/模块连线、架构、运行时兼容、
  依赖姿态、验证与部署就绪，以及明显的安全或可靠性信号。适用于「审查我的应用」「能不能发布」
  「部署前检查」。不要用于新建/改功能或讲解执行怎么部署/分发（nexus-app-builder）、
  安全审计/漏洞评估/AuthZ 深挖（nexus-security-reviewer）或诊断已知故障（nexus-app-debugger）。
license: MIT
metadata:
  maintainer: pingcode
  namespace: nexus
  labels: nexus,reviewer,readiness
---

# Nexus App Reviewer

## 何时使用

应用**已有实现**，用户要做发布前 / 提交前就绪检查（「能不能发布」而非「怎么部署」）。  
新建/部署讲解 → `nexus-app-builder`；现网报错 → `nexus-app-debugger`；安全审计/漏洞评估 → `nexus-security-reviewer`。

## MUST

1. 先审计，默认**不改代码**；按 `references/review-checklist.md` 产出通过 / 阻塞 / 建议。
2. **开始前打开并读完** [references/boundaries.md](references/boundaries.md) 与 [references/platform-invariants.md](references/platform-invariants.md)。
3. 读 `manifest.yaml`（优先于 `.yml`）与相关源码；运行 `nexus lint` 作证据。
4. 明显安全信号可记录并建议转 `nexus-security-reviewer`，**不默认**完整 SAST/`npm audit`。
5. **知识原则**：打开 [references/review-checklist.md](references/review-checklist.md)；字段/SDK/扩展点按条件查证（[references/docs-online.md](references/docs-online.md)），勿整目录预读、不猜测。
6. 不索要 token；不执行 deploy/distribute，除非用户明确要求。

## NEVER

- 把审查当成故障复现与热修主路径
- 用未核实资料判定平台规范
- 无证据标「阻塞」；把推测安全观察写成已确认漏洞
- 因干净 checkout 缺少 `web/main/dist` 而误报阻塞（dist 常被 gitignore）
- 把缺失 `app.name` 当成错误（应用名在开发者中心）

## 工作流

1. Manifest：extensions / resources / functions / permissions / events / remotes / exposer / storage / async / env——核对引用一致性。
2. `package.json`（根与 `web/main`）：`@pc-nexus/*`、scripts、Node ≥ 24。
3. 源码：Resolver/`api.invoke` 身份、Bridge invoke 名、错误处理、异步与超时。
4. `nexus lint` → 按 checklist 写结构化报告（格式见 checklist）。
5. 深度安全 / 现网故障分别交接对应 skill。

## 参考

`references/review-checklist.md` 及共用 boundaries / invariants / docs-online。
