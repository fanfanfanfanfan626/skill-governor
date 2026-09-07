# Skill Governor：AI Agent Skill 治理规范

[English](README.md) · [AI 安装说明](AI_INSTALL.md) · [项目主页](https://fanfanfanfanfan626.github.io/skill-governor/) · MIT 开源许可 · 1.0.0

一个开源、本地优先的 AI Agent Skill 治理工具。它把“什么时候用 Skill、先读什么、多个 Skill 怎么选、新增和更新怎么处理、到底有没有用”整理成一套可执行、可审计、可回退的规则。

它是一项通用 Skill。AI 读取真实环境后制定适合当前用户的规则；Python 工具负责只读审计、登记、变更检测、证据一致性检查和可回退的规则接入。个人技能名单、路径和审查记录保留在各自的私有状态目录。

它最适合 Skill 较多、触发范围重叠、存在多个安装来源或需要跨设备迁移的环境。简单任务只有一个明确专家 Skill 时，不需要额外调用它。当前实现以 Codex 为首要宿主，也可以作为指令包迁移到兼容 Skill 文件夹的其他 Agent 宿主；宿主能否发现、持续路由和提供工具权限，仍需分别验证。

## 怎么安装

1. 下载或克隆本仓库。
2. 将整个 `skills/skill-governor` 文件夹复制到宿主支持的 Skill 目录；已有同名目录时先检查版本。
3. 按宿主支持的方法重新加载，确认 `skill-governor` 出现在可用清单。
4. 可选脚本需要 Python 3.10+ 和 PyYAML 6。在仓库根目录执行：

```sh
python -m pip install -r requirements.txt
```

只复制 Skill 文件夹时，使用该文件夹自带的 `requirements.txt`。Codex 用户也可以通过 Skill 安装器选择仓库中的 [`skills/skill-governor`](skills/skill-governor) 子目录。准确的包身份、AI 安装步骤和验证方法见 [AI_INSTALL.md](AI_INSTALL.md)。其他宿主需要确认其 Skill 格式和规则入口是否兼容。

## 怎么使用

直接对 AI 说：

> 使用 $skill-governor，检查我的 Skill 清单，规划什么时候用什么、必须读什么，并把这一套治理规则落实到当前项目。

也可以限定范围：

> 使用 $skill-governor，只审查不修改，列出重复能力、适用条件、必读文档和缺失依赖。

> 使用 $skill-governor，检查这个新增 Skill 是否有实际价值、和现有 Skill 怎么分工，再按已授权范围安装和登记。

> 使用 $skill-governor，检查更新后的 Skill，重新审查变动内容和受影响的选择规则。

## 它会怎样处理

| 环节 | 规则 |
|---|---|
| 盘点 | 根据宿主清单和明确目录发现 Skill，不扫描整个用户目录 |
| 规划 | 阅读实际内容，制定适用条件、排除条件、项目边界和阶段分工 |
| 选择 | 尊重明确点名、项目要求和工具前置条件；简单任务允许不用 Skill |
| 阅读 | 使用前读完整 SKILL.md 和当前适用的必读文件；描述、摘要和“已读”标记不能替代正文 |
| 执行 | 确认真实工具与权限，保留授权边界，缺失依赖如实说明 |
| 新增 | 查来源、能力增量和重叠，按宿主方式安装，登记并审查 |
| 更新 | 文件或引用内容变化后标记需复核；刷新清单不等于重新审查 |
| 评估 | 根据任务结果和成本判断有用、条件适用、可能重复、当前不支持或待评估 |
| 退出 | 删除或禁用需要相应授权；自己的规则接入提供备份和回退 |

已有治理体系时优先合并和维护，避免再加一套互相冲突的全局规则。规则规模随技能库调整：小清单可用一张表，大清单再分领域。

## 可选命令

下面是可直接运行的仓库自身示例：

```sh
python skills/skill-governor/scripts/govern.py --state .skill-governance init --source personal=skills
python skills/skill-governor/scripts/govern.py --state .skill-governance plan
python skills/skill-governor/scripts/registry.py --root .skill-governance check
```

首次检查出现“未分类、未审查”是正常结果。初始化只生成草案；AI 需要阅读来源并编写当前环境的 POLICY.md，才能接入宿主规则。完整命令、字段、退出码与回退说明见 [CLI 文档](skills/skill-governor/references/cli.md)。

如果只想做不产生治理状态的结构与路由审计：

```sh
python skills/skill-governor/scripts/audit_skills.py --root skills --format markdown --fail-on-issues
```

## 能保证到什么程度

安装一个 Skill，并不意味着 AI 每次都会选中它。持续使用需要把简短指引接入已经确认有效的宿主规则入口。这是指令层规范，不能保证每次自动遵守，也不是安全隔离系统。

“文件存在”“读过来源”“工具可用”“实际执行过”“结果验证通过”“用户接受”分别记录。文件哈希只能绑定版本；证据检查不能证明 AI 真正理解正文，也不能替代真实任务效果评估。脚本不执行被审查的 Skill、不联网、不发布仓库、不建立后台监控。同一状态目录的修改需要串行执行。

## 测试与开源

```sh
python skills/skill-governor/scripts/audit_skills.py --root skills --format markdown --fail-on-issues
python -X utf8 -m unittest discover -s tests -v
```

当前包含 63 项单元测试，全部使用临时目录。仓库已配置 Windows、Linux、macOS 和 Python 3.10/3.13 的 CI；是否通过必须看实际运行结果，不能把配置当成测试证据。

发布时只包含通用源文件。不要提交生成的技能清单、个人路径、凭据、项目关联、审查记录或备份；交付前还要检查最终文件清单与压缩包内容。

采用 [MIT 许可证](LICENSE)，允许使用、修改和再分发。被审查的第三方 Skill 仍遵循它们各自的许可证和要求。
