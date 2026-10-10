# skill4research

通用科研多 agent 技能：论文复现，以及持续的文献—假设—实验—反思循环。

## Skills

| Skill | 用途 |
|---|---|
| [paper-reproduction-team](skill4research/skills/paper-reproduction-team/SKILL.md) | 规划、独立计划核查、执行修改、独立实现与结果核查；追踪论文配方与实测证据 |
| [overnight-research-loop](skill4research/skills/overnight-research-loop/SKILL.md) | 提案、idea 把关、独立验证反思与执行；实时反馈、机制多样化和项目经验学习 |

候选数量、研究领域、评价集合、门槛和资源由每次任务确定。把关者对放行理由负责，反思者独立核查其判断；负证据及时通知相关活跃 agents，按证据修订、诊断、放弃或转向。

## 使用

将 `skill4research/skills/` 中两个完整目录复制到宿主支持的个人或项目技能目录，保留 `agents/`、`references/` 相对关系。确认宿主可用技能列表后，使用 `$paper-reproduction-team` 或 `$overnight-research-loop` 调用；也可以直接让 agent 读取对应 `SKILL.md` 执行。

- [详细使用说明](skill4research/START-HERE.md)
- [探索流程角色与权限](skill4research/skills/overnight-research-loop/references/research-roles.md)
- [质询、反馈、多样性与经验](skill4research/skills/overnight-research-loop/references/feedback-and-diversity.md)
- [复现流程角色与交接](skill4research/skills/paper-reproduction-team/references/agent-roles.md)
- [六个项目的源码编排调研](skill4research/PROJECTS.md)
- [当前通用版本的行为审阅](skill4research/GENERIC-BEHAVIOR-REVIEW.md)
- [结构检查记录](skill4research/VALIDATION.json)

## 边界

技能规定工作流程，不自带后台调度、持久运行服务或科研执行环境。结构检查与场景审阅不证明科学有效性、复现成功或通宵运行可靠性。角色轮转遵循宿主并发限制，不扩大计算授权。旧版行为审阅仅保留为历史记录，当前规则以 skill 文件为准。
