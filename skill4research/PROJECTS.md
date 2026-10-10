# 别人如何编排科研 Agent：六个项目的源码核查

核查日期：2026-10-10。仅阅读官方仓库、工作流和核心实现；没有安装或执行这些项目，也没有验证其科研产出。下文“已核实”指阅读到的实现/文档事实，“建议”指针对你的任务作出的设计判断。main/master 链接会变化，实际采用前应冻结 commit。

你最值得组合的是：Agent Laboratory 的角色交接、AI Scientist v2/AIDE 的实验谱系、autoresearch 的固定评估闭环、autoresearch-paper 的独立监督和恢复、K-Dense 的分层技能结构。没有一个已读项目可以直接保证“四个 agent 就能完全复现论文表格”或“写了 NEVER STOP 就能可靠运行整夜”。

| 项目 | 编排单位 | 可借鉴部分 | 对你仍缺什么 |
|---|---|---|---|
| Agent Laboratory | 专业角色与阶段交接 | 计划、实施、解释、评审分工 | 表格配方逐项对应；客观验收门槛 |
| AI Scientist v2 | 阶段内实验树和并行节点 | 节点谱系、最佳实现继承、多种子、checkpoint | 固定论文协议审计；整夜持久监督 |
| AIDE | draft/debug/improve 节点搜索 | 失败与有效节点分开；从最佳节点深化 | 独立计划审查；可验证指标提取 |
| karpathy/autoresearch | 单文件修改—训练—保留/回退 | 固定预算、评估不变、每轮台账 | 多 agent、独立 watchdog、领域适配 |
| WdBlink/autoresearch-paper | Host/Worker/Controller/Watchdog | 文件状态、证据绑定、外部触发恢复 | Windows/Linux 调度适配；长期稳定性实测 |
| K-Dense Scientific Agent Skills | 小型程序性知识 skill | 假设、替代解释、预测、测量分别建档 | 实验执行器与监督器；自动 top2 策略 |

## 1. Agent Laboratory：角色真实存在，但“评审”不等于客观基准

**已核实：** `LaboratoryWorkflow` 实例化 PhD、Postdoc、Professor、ML Engineer、SW Engineer 和 Reviewers；依次经过文献、计划、数据准备、实验、解释、写作。阶段状态可以保存；评审后存在返回实验的路径，但当前默认 `review_override=True`、`review_total_steps=0`，不能据此认为默认持续科研。[工作流源码](https://github.com/SamuelSchmidgall/AgentLaboratory/blob/main/ai_lab_repo.py)

**关键边界：** `MLESolver.get_score()` 让 LLM 根据计划、代码和输出生成 0—1 分，`best_codes` 按该分保留。它并非固定 benchmark accuracy 或论文表格差值。[实验求解器源码](https://github.com/SamuelSchmidgall/AgentLaboratory/blob/main/mlesolver.py)

**建议：** 借交接方式，但把角色改为“计划→计划审查→执行修改→独立核查”。计划审查要看论文原文，最终核查要重新读取代码、配置、输出；验收同时要求配方符合和客观指标可追溯，不能用 LLM 主观评分替代。

## 2. AI Scientist v2：重点是实验树和阶段推进，而非角色数量

**已核实：** manager 明确划分 initial implementation、baseline tuning、creative research、ablation；每阶段维护 journal，继承上一阶段最佳实现；阶段完成时有 multi-seed evaluation，保存含 journal/配置/阶段的 checkpoint。其完成判据既有迭代上限，也有 LLM 对图表及结果的判断。[AgentManager](https://github.com/SakanaAI/AI-Scientist-v2/blob/main/ai_scientist/treesearch/agent_manager.py)

配置提供 parallel workers、分阶段迭代上限、三种子设置和执行 timeout，说明并行宽度和运行预算由运行器管理。[配置](https://github.com/SakanaAI/AI-Scientist-v2/blob/main/bfts_config.yaml)

**建议：** 借实验节点谱系、最优候选继承、多种子复验。你的 top2 应是保留两个值得深化的方向，再根据预算选择执行；不需要把“每轮必须恰好两个”变成硬规则。配方复现则冻结论文主配方，避免直接采用其 baseline tuning 阶段改参数。

**具体源码风险：** launcher 清理末尾还会遍历全机进程，并按命令行含 `python/torch/mp/bfts/experiment` 等关键词尝试终止；在共享 GPU/服务器上不能照搬。应按本 run 的 job ID、进程起始身份及所有权清理。[启动脚本](https://github.com/SakanaAI/AI-Scientist-v2/blob/main/launch_scientist_bfts.py)

## 3. AIDE：一个简单但有效的“有谱系的搜索”

**已核实：** `search_policy()` 先生成 drafts；在概率和 debug-depth 约束下修复 buggy leaf；没有有效节点时继续 draft，否则挑最佳节点改善。`step()` 将计划/代码、执行结果和反馈加入 journal；改善提示要求一个可单独评估的改动。结果解析由反馈模型读取日志，标记异常/缺指标/NaN，提取指标值。[agent.py](https://github.com/WecoAI/aideml/blob/main/aide/agent.py)

**建议：** 借“错误修复与科学方向失败分开”“用历史避免重复”“从有用节点继续”。你的 gate 应读取机器生成的逐样本结果文件，LLM 负责解释，避免仅靠模型从文本日志读取数字就决定晋级。源码中计划与代码可在同次调用生成，不满足你要求的独立计划核查。

## 4. karpathy/autoresearch：最接近“夜里不断试”的最小闭环

**已核实：** `program.md` 要求先跑 baseline、只改 `train.py`，记录 commit/metric/memory/status，改善则保留否则回退；单 GPU，每轮训练预算五分钟，超时按失败处理。评估与数据准备放在不允许修改的 `prepare.py`，其中固定时间常量和 validation shard。[循环指令](https://github.com/karpathy/autoresearch/blob/master/program.md)、[固定数据/评估](https://github.com/karpathy/autoresearch/blob/master/prepare.py)

**边界：** 指令要求持续直到人工中断，但这不等于外部调度、断线恢复或无人值守可靠性；一次五分钟训练也不能直接类比你的一轮视觉 benchmark 推理成本。

**建议：** 借“冻结 evaluator＋每轮落盘＋keep/discard/crash＋下一轮明确继续”。对视觉增强要额外记录实际 forward 数、输入/输出 token、GPU 秒和延迟；用固定资源评估公平性，明确预算上限和授权工作时间。

## 5. WdBlink/autoresearch-paper：最贴近长期监督，但不能把文档当可靠性实测

**已核实：** SKILL 描述 Codex Host、独立 Claude Code Worker、确定性 Controller、文件证据、冻结 evaluator、写作前 gate。它明确说明当前有界验证不代表 24h/7x24 稳定或生产就绪。[SKILL.md](https://github.com/WdBlink/autoresearch-paper/blob/main/skills/autoresearch-paper/SKILL.md)

运行器中 `command_dispatch_worker()` 核查 deadline/状态/合同，`record_worker_heartbeat()` 保存心跳；`command_run_runtime_assurance_tick()` 可以重载 L1，并做不调用模型的 health patrol。L0/L1 的当前实现使用 `launchctl`/launchd plist，不能当作已支持 Windows 的整夜监督器。[harness-runtime.py](https://github.com/WdBlink/autoresearch-paper/blob/main/skills/autoresearch-paper/references/scripts/harness-runtime.py)

**建议：** 借“独立于当前聊天的监督器、canonical state、运行身份绑定、科学无改善和进程卡住分别处理”，不照搬其全部审批及复杂跨产品机制。你明确授权的一晚应在初始合同里包括继续迭代、修复、重跑和晋级预算，日常动作无需反复询问。Windows 可由任务计划程序、Linux 可由持久服务实现，但这些必须实际部署并验证。

## 6. K-Dense Scientific Agent Skills：适合拆能力，不负责启动科研循环

**已核实：** `hypothesis-generation` 分离 observation/question/hypothesis/mechanism/prediction/measurement/evidence，附 JSON/CSV 模板及本地结构检查工具；`scientific-critical-thinking` 独立负责设计、偏差与证据审查，通过 references 按需展开。[假设 skill](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/hypothesis-generation/SKILL.md)、[证据审查 skill](https://github.com/K-Dense-AI/scientific-agent-skills/blob/main/skills/scientific-critical-thinking/SKILL.md)

**关键适配：** 当前 hypothesis skill 明确禁止自动给科学假设排名/选取；它不能原封不动支持你的 top2 自动迭代。其大量临床/伦理框架也不必全部搬入 ML 实验。

**建议：** 借结构化记录和渐进加载；你自己的 skill 可以根据预期收益、证据、成本、历史重复性选取候选，但必须记录不确定性，后续按实测更新。这里阅读其结构作为案例，没有加载为本任务的执行规则。

## 对本技能包的设计判断

这些是针对你的需求作出的建议，不是上述项目已经提供的能力：

1. **配方复现：** 表格行/列→正文/附录/代码来源→配置→运行产物→数值差异，形成逐项核查链。独立核查不能只看执行 agent 的摘要。协议一致与数值接近分别验收；不能为了碰到论文数字而更改 protocol。
2. **夜间研究：** 候选方向→独立预检→有意义的中间分析→小集合筛选→晋级复验→结果反思→新候选。每轮记录前一判断如何被结果修改。不同名称但机制相同的失败方向要判重。
3. **数据集合：** “baseline 错误集合＋部分原来正确样本”有意富集错误，是 discovery set。它适合筛选修复和观察回归，不是无偏 benchmark 平均成绩。分别报错误修复率、正确回归率和混合集分数。候选晋级后用预先冻结、未用于持续选择的半 benchmark 对比；若反复查看它来选后续方法，它也成为开发集，应保留另一部分作最终确认。
4. **增益门槛：** `+x%` 必须定义为百分点或相对百分比，并注明比较样本、重复/种子、成本上限。筛选阈值与统计显著性不能混为一谈；持续多轮挑最佳会有选择偏差，需要独立复验。
5. **持续性：** SKILL 是工作规则，运行器执行，监督器发现停滞并恢复。只有看到调度注册、有效 heartbeat、真实进程/job 身份、状态落盘与一次恢复演练，才能把状态叫作“已部署”。创建技能文件不能保证明早聊天仍在运行。

未安装任何外部项目；没有为本任务建立夜间服务，也没有启动 GPU 实验。
