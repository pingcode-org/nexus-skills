---
name: nexus-security-reviewer
description: >-
  对 PingCode Nexus 应用执行结构化白盒安全审查，产出证据驱动的审计报告（含 CVSS、代码证据与验证步骤）。
  适用于安全审查、漏洞评估、AuthZ、租户隔离、Webhook/Exposer 加固或静态分析。
  不要用于通用 PingCode 配置审查、发布就绪泛查（nexus-app-reviewer）或现网故障诊断（nexus-app-debugger）。
license: MIT
metadata:
  maintainer: pingcode
  namespace: nexus
  labels: nexus,security,audit
---

# Nexus Security Reviewer

## 何时使用

用户明确要求安全审查 / 审计 / 越权与租户隔离 / Webhook 加固 / 完整静态分析时使用。

## MUST

1. 按 [references/security-audit-method.md](references/security-audit-method.md) 执行：**manifest 摘要脚本 → 全局规则 → 按需分类规则**。
2. **开始前打开并读完** [references/boundaries.md](references/boundaries.md) 与 [references/platform-invariants.md](references/platform-invariants.md)。
3. 产物写入项目外的 `ARTIFACT_DIR`；强调服务端鉴权，`display` 非安全边界。
4. 已确认发现含证据、成立条件、影响、CVSS、修复建议与可复现验证步骤。
5. 不在对话中接收 token；发现硬编码凭据时指导轮换与移除。
6. 除非用户要求修复，不改应用代码。
7. **知识原则**：按信号打开下方规则路径；字段/API 按条件检索（[references/docs-online.md](references/docs-online.md)），勿整目录预读。

## NEVER

- 无代码/配置证据的高危断言
- 夸大工具能力（无官方跨过程 SAST、无 endpoint↔scope 映射表）
- 用未核实资料判定权限/API 规范
- 把扫描产物写入被审项目源码树
- 把发布质量清单整份重做（`nexus-app-reviewer`）或替代现网排障（`nexus-app-debugger`）

## 工作流摘要

1. `ARTIFACT_DIR=...`；在本 skill 目录运行 `python3 -m scripts.summarize_manifest <root> ...`
2. 读摘要与 `observations`（线索需规则验证）。
3. 先加载 [assets/security-rules/_global-nexus.mdc](assets/security-rules/_global-nexus.mdc)。
4. 按下方信号表打开对应 `_index-*.mdc`，**仅命中启发式时**再打开子规则（完整相对路径）。
5. 追踪 来源 → 校验/授权 → 汇聚点；确认可利用性后再写入正式发现。
6. 输出 Markdown 审计报告；告知用户 `ARTIFACT_DIR` 路径。

## 信号 → 规则（从技能根目录）

| 信号 | 先打开索引 | 常见子规则 |
| --- | --- | --- |
| scope / 写操作 / `as: "app"` | [assets/security-rules/nexus-authn-authz/_index-authn-authz.mdc](assets/security-rules/nexus-authn-authz/_index-authn-authz.mdc) | [asapp-privilege-escalation.mdc](assets/security-rules/nexus-authn-authz/asapp-privilege-escalation.mdc)、[missing-resolver-authz.mdc](assets/security-rules/nexus-authn-authz/missing-resolver-authz.mdc)、[prefer-context-authz.mdc](assets/security-rules/nexus-authn-authz/prefer-context-authz.mdc)、[display-conditions-bypass.mdc](assets/security-rules/nexus-authn-authz/display-conditions-bypass.mdc) |
| webhook / exposer | [assets/security-rules/nexus-webhook-entrypoints/_index-webhook-entrypoints.mdc](assets/security-rules/nexus-webhook-entrypoints/_index-webhook-entrypoints.mdc) | [webhook-security.mdc](assets/security-rules/nexus-webhook-entrypoints/webhook-security.mdc) |
| external.fetch / remotes / fetch.request | [assets/security-rules/nexus-egress-remotes/_index-egress-remotes.mdc](assets/security-rules/nexus-egress-remotes/_index-egress-remotes.mdc) | [wildcard-permissions.mdc](assets/security-rules/nexus-egress-remotes/wildcard-permissions.mdc)、[data-egress-redirects.mdc](assets/security-rules/nexus-egress-remotes/data-egress-redirects.mdc) |
| XSS / RCE / SSRF 等 sink | [assets/security-rules/nexus-injection/_index-injection.mdc](assets/security-rules/nexus-injection/_index-injection.mdc) | [ssrf.mdc](assets/security-rules/nexus-injection/ssrf.mdc)、[xss.mdc](assets/security-rules/nexus-injection/xss.mdc)、[rce-code-execution.mdc](assets/security-rules/nexus-injection/rce-code-execution.mdc)、[sql-injection.mdc](assets/security-rules/nexus-injection/sql-injection.mdc)、[prototype-pollution.mdc](assets/security-rules/nexus-injection/prototype-pollution.mdc) |
| 全局状态 / 存储 key | [assets/security-rules/nexus-tenant-isolation/_index-tenant-isolation.mdc](assets/security-rules/nexus-tenant-isolation/_index-tenant-isolation.mdc) | [global-state-warmstart.mdc](assets/security-rules/nexus-tenant-isolation/global-state-warmstart.mdc) |
| 凭据 / env / KVS secret | [assets/security-rules/nexus-secrets-storage/_index-secrets-storage.mdc](assets/security-rules/nexus-secrets-storage/_index-secrets-storage.mdc) | [hardcoded-secrets.mdc](assets/security-rules/nexus-secrets-storage/hardcoded-secrets.mdc) |
| 过宽 scope、CSP、通配域名 | [assets/security-rules/nexus-manifest-config/_index-manifest-config.mdc](assets/security-rules/nexus-manifest-config/_index-manifest-config.mdc) | [permission-scopes.mdc](assets/security-rules/nexus-manifest-config/permission-scopes.mdc)、[egress-url-entries.mdc](assets/security-rules/nexus-manifest-config/egress-url-entries.mdc)、[content-security-policy.mdc](assets/security-rules/nexus-manifest-config/content-security-policy.mdc) |
| 完整静态扫描 | [assets/security-rules/nexus-auditing/_index-auditing.mdc](assets/security-rules/nexus-auditing/_index-auditing.mdc) | [static-analysis-nexus.mdc](assets/security-rules/nexus-auditing/static-analysis-nexus.mdc) |
| SCA / 依赖 | [assets/security-rules/nexus-misc/_index-misc.mdc](assets/security-rules/nexus-misc/_index-misc.mdc) | [software-composition.mdc](assets/security-rules/nexus-misc/software-composition.mdc) |

聚焦模式（例如「只看 AuthZ」）：全局基线 + 该行索引与匹配子规则。  
详细步骤与限制见 [references/security-audit-method.md](references/security-audit-method.md)。

## 交接

修复实现可交 `nexus-app-builder`；审查中发现现网故障线索可提示 `nexus-app-debugger`；通用就绪检查属 `nexus-app-reviewer`。
