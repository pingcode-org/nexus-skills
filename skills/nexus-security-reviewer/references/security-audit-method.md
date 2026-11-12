# 安全审查方法（内置）

白盒、证据驱动。默认 **manifest 驱动按需加载规则**，勿一次读入全部规则文件。

## 执行步骤

1. 在**目标项目外**建临时目录：`ARTIFACT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/nexus-security-review.XXXXXX")"`
2. 运行（在本 skill 目录）：
   ```bash
   python3 -m scripts.summarize_manifest <project-root> --format markdown
   python3 -m scripts.summarize_manifest <project-root> --format json -o "$ARTIFACT_DIR/manifest-summary.json"
   ```
3. 先读摘要：entrypoints、scopes、egress、remotes、exposer、events、storage、observations（线索≠已确认漏洞）。
4. 加载 `assets/security-rules/_global-nexus.mdc`，再按 `SKILL.md` 信号表打开对应 `_index-*.mdc`，仅在命中启发式时读子规则（路径一律从技能根目录写起）。
5. 扫描产物一律写入 `ARTIFACT_DIR`，**禁止**写入被审项目源码树。
6. 除非用户要求修复，不改应用代码。

## 信号 → 规则分类（完整相对路径）

| 信号 | 索引 |
| --- | --- |
| scope / 写操作 / `as: "app"` | `assets/security-rules/nexus-authn-authz/_index-authn-authz.mdc` |
| webhook / exposer | `assets/security-rules/nexus-webhook-entrypoints/_index-webhook-entrypoints.mdc` |
| external.fetch / remotes / fetch.request | `assets/security-rules/nexus-egress-remotes/_index-egress-remotes.mdc` |
| XSS/RCE/SSRF 等 sink | `assets/security-rules/nexus-injection/_index-injection.mdc` |
| 全局状态 / 存储 key 作用域 | `assets/security-rules/nexus-tenant-isolation/_index-tenant-isolation.mdc` |
| 凭据 / env / KVS secret | `assets/security-rules/nexus-secrets-storage/_index-secrets-storage.mdc` |
| 过宽 scope、CSP、通配域名 | `assets/security-rules/nexus-manifest-config/_index-manifest-config.mdc` |
| 完整静态扫描 | `assets/security-rules/nexus-auditing/_index-auditing.mdc` |
| SCA / 依赖 | `assets/security-rules/nexus-misc/_index-misc.mdc` |

子规则路径形如 `assets/security-rules/<category>/<rule>.mdc`。索引与规则正文中的互引也必须使用该形式，**不要**使用 `@category/rule.mdc` 别名。

## 必须覆盖

- AuthZ：`as: "app"` 越权、Resolver/Exposer 缺授权、`display` 绕过
- 注入与输入校验；租户隔离（FaaS warm start、全局缓存、存储 key）
- 密钥与存储；出站/CSP/NIT；Webhook/事件公开入口

## 报告

已确认发现按 CVSS v3.1 排序，含：向量与评分、可利用性与影响、文件证据与来源→汇聚点、CWE、可复现验证步骤。  
不可利用的加固观察放「需验证」。标注假设与证据缺口。

## 已知限制（勿夸大工具能力）

- 无跨过程官方 SAST；结论须说明是代码追踪而非自动分析器。
- 无公开 REST endpoint↔scope 映射 → 不能机械判定最小化 scope。
- Semgrep 仅社区 ruleset；自定义 Nexus rules 未内置。
- `summarize_manifest.py` 只解析 manifest，不解析业务代码。

通用就绪 → `nexus-app-reviewer`；现网故障 → `nexus-app-debugger`。
