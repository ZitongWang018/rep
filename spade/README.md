# SPADE 4B 工具任务复现：迁移与测试交接

> 更新：2026-10-10。目标是复现 SPADE 已披露的工具任务主配方，测试 Qwen3-4B-Instruct-2507 在 τ²-bench 上的训练前后变化。允许调整卡数，以及使用 DeepSeek 替代 GPT-4.1 用户模拟器和自然语言评委。本文可以直接交给另一台机器上的执行者。

## 1. 交给执行者的任务

请先确认已有模型和环境，避免重复下载；全部安装、缓存、数据、生成环境和检查点放在我的个人目录中，不改系统环境、不清理其他人的进程。先运行 CPU 机制检查，再做 GPU 启动检查和完整训练。训练必须遵守下文的 hint 对照、奖励时点、完整样本和检查点规则；不能只照搬作者公开启动器。训练前后使用同一套冻结的 τ² 评测协议。每 10 分钟检查一次训练状态，异常必须给出阶段、实际样本数、错误原因和恢复是否完整。

首要交付：环境版本清单、五类 CPU 检查结果、首次真实 GPU 更新、第一轮生成器成熟更新、首个完整成对检查点、完整基线和最终模型的三域指标。不要把“能启动”或“CPU 测试通过”称为复现成功。

## 2. 仓库提供什么

- 本文：实验规范、迁移步骤、通过标准和故障处理。
- `configs/reproduction.json`：脱敏的训练与评测目标参数，**不是训练器直接读取的启动配置**。
- `configs/source-lock.json`：已审查训练源码、依赖和启动检查文件的 SHA256，用于核收迁移源码。
- `scripts/verify_source_lock.py`：仅使用 Python 标准库的源码核收工具。
- `.env.example`：新机器路径与服务配置模板，不含密钥。

这里没有模型权重、完整训练依赖、语料、任务原文或现有服务器日志。完整修复源码需要从现有复现项目另外迁移；只克隆作者仓库不会获得我们的修复。核收工具用于**适配前**确认收到的是同一版本；改动路径或启动脚本后，应另存迁移差异和新哈希，不能沿用原审查结论冒充新机器已验证。

## 3. 来源和实验范围

| 项目 | 固定来源 |
|---|---|
| 论文 | [SPADE: Self-Play in Adaptive Synthetic Executable Environments](https://arxiv.org/abs/2608.19197)，主配方见 [§5.1、§5.3](https://arxiv.org/html/2608.19197v3#S5) |
| SPADE 作者代码 | [spade-rl/spade](https://github.com/spade-rl/spade)，本地基底 `ebd40ec872fc5630cac299cb5e38e7c89743bef5`，另有已审查修复 |
| Slime | [THUDM/slime](https://github.com/THUDM/slime)，本地 checkout `bf14dc21f9500746447f2572d0692e981c4d2a7e`；实际文件版本以 source-lock 为准 |
| 动态批处理来源 | `799893808039c1d61a1bf369718fe817000ff652` 的历史实现，不能把它误认为整个当前 Slime 的 HEAD |
| 原始模型 | [Qwen/Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)，必须是 Instruct-2507 |
| 训练语料 | [spade-rl 模型与数据](https://huggingface.co/spade-rl) 中的 `SPADE-Grounding-Corpus-ToolUse-15K`，15,000 条 grounding 文档 |
| 评测代码 | [τ²-bench](https://github.com/sierra-research/tau2-bench)，固定历史快照 `a2c024725189473d2d7cea3a5cfdbcc67478e41f` |

本轮只做**工具任务训练与 τ² 评测**。τ² 是多轮用户交互、工具调用和状态约束任务，不是单题数学推理，也不是 WebArena 浏览器导航。不需要为本轮补 BFCL、ACEBench 或 ALFWorld。Grounding 语料用于生成训练环境，不等于 τ² 测试集；禁止用评测任务指导生成器或训练 solver。

论文未公开工具运行的全部私有参数；附录 Table 5 主要描述 games 配方，工具换题间隔按 §5.3 使用 8。下述奖励带宽、实施选择和截止轮处理必须披露，不能声称除卡数和 DeepSeek 外已经证明所有作者内部细节完全一致。

## 4. 新机器的准备与迁移

推荐 Linux，使用个人虚拟环境或个人容器。现有验证机器为 4×A100-SXM4-40GB，TP=2、CP=2、PP=1、DP=1。四卡 4090 的 24GB 显存和互联条件不同，**尚未验证可支撑该设置**；不能通过减少环境数、hint 次数或序列长度来默默改变实验。

现有训练运行时：Python 3.12、PyTorch `2.11.0+cu129`、SGLang `0.5.12.post1`，以及兼容的 Megatron、Transformer Engine、FlashAttention、FlashInfer、Ray 和 memory-saver。此清单不是完整依赖锁；迁移时需要另外导出现有环境版本、容器指纹、私有 overlay 文件及哈希。不要直接混装最新版本。

建议目录：

```text
<个人数据目录>/spade-reproduction/
  upstream/             # SPADE 与 Slime，以及经过审查的修复
  assets/               # grounding corpus
  models/               # 已有原始 Instruct 模型，或个人目录内的引用
  workspace/            # 固定版本 τ² 代码和数据
  envs/                 # 训练和评测依赖分别管理
  runs/<run-id>/         # 本轮环境、奖励测量、权重
  logs/                 # 状态和诊断，禁止公开密钥及原始对话
  evidence/             # 源码哈希、协议和检查报告
```

迁移顺序：

1. 找到已有 Instruct 模型、语料和个人环境，校验模型类型与文件完整性；不要重新下载 base 模型。
2. 从现有项目核收修复源码、五个检查脚本、训练启动器、监控及检查点审计工具。现有完整部署包为 80 个文件；其余依赖、模型和数据需要单独准备。
3. 适配前执行 `python scripts/verify_source_lock.py --project-root /你的个人目录/spade-reproduction`。任何哈希差异必须先解释。
4. 修改硬编码的项目路径、UID 所属检查、Slurm 分区、容器路径、模型路径、端口和任务目录；这些检查不能直接删除。UID 使用新机器实际本人 UID，并核查解析后的路径仍在个人目录内。
5. 用个人虚拟环境或容器完成依赖检查，并保存迁移差异、新源码锁和实际启动参数。
6. 确认每个训练作业有独立 Ray 临时目录和服务端口；禁止全局 `pkill`、`ray stop`，禁止复用旧任务缓存目录。
7. API 凭据只从本机环境变量或权限受限配置读取。`.env.example` 仅供参考；旧 provider runner 使用私有配置文件，需适配它的凭据读取方式，不能假设设置变量就自动接通。

原始 HF→Megatron DCP 转换后，应逐张量核对：398 个逻辑张量、4,022,468,096 个逻辑参数；已有 TP2 格式词表填充到 152064 行，物理元素为 4,022,795,776。词表填充可解释，不允许用原模型补填其他缺失张量。改变分片方式时，应比较全局逻辑张量，不能只对比 shard 文件名。

## 5. 必须保持的训练配方

| 参数 | 本轮目标 |
|---|---|
| 真实优化器更新次数 | 400，编号 0…399 |
| 每轮有效环境 | 24；当前 3 个技能，每技能 8 个，轮换覆盖 6 个技能 |
| 每环境无 hint 轨迹 | 每轮 16 条，共 384 条 |
| 每环境有 hint 轨迹 | 换题时额外 16 条，仅用于匹配对照，不另做一次 solver 更新 |
| 换题 / 生成器延迟更新 | 均为 8 轮 |
| 两侧 actor 温度 / 输出预算 | 均为 0.6 / 8192 token |
| 上下文 / 最大交互轮数 | 32768 / 25 |
| 环境生成器温度 / 输出预算 | 0.6 / 16384 token |
| 环境记忆 | 200 条，最早写入的先移除，新 run 重新初始化 |
| 学习率 / Adam betas / weight decay | 1e-6 / (0.9, 0.98) / 0.1 |
| KL / entropy 系数 | 均为 0 |
| PPO clip / TIS | 下侧 0.2、上侧 0.28；启用 TIS |
| 名义 batch | 192；保持历史 Slime 动态批处理 |
| 实际 actor / 混合 batch | 384 / 408，完整数据一次更新，不裁剪、重复或再归一化 |
| 权重保存 | 每 40 次真实更新，即 39/79/…/399；仅保留最新完整成对点 |

每个 8 轮窗口产生 3072 条无 hint 回报；生成器成熟时加入旧池的 24 条生成轨迹，形成 408 个训练样本。24 条有 hint 对照不是这 24 条生成器轨迹，不能混淆。

更新 8…392 共成熟 49 个旧环境池，最终应有 1176 条成熟生成器样本。第 392 轮生成的池到第 400 轮才成熟，但最后更新是 399；不提前清空延迟、不额外增加第 400 次编号更新。调度器最终累计样本数应为 `400×384 + 49×24 = 154776`。

本地实施选择：hint writer 温度 0.3、输出 512；validator 温度 0.3、输出 16384；生成器按技能中心化后沿用公开实现的放大系数 50。这些数值不应冒充论文全部公开的工具专用设置。

## 6. Hint、奖励与数据正确性：重点检查

### 6.1 Regret 的时点

在换题轮 `t`，使用**同一份冻结策略**分别取得 16 条有 hint 和 16 条无 hint 回报：

```text
regret = mean(hint_returns_at_t) - mean(plain_returns_at_t)
regret_norm = clip(regret / 0.15, 0, 1)
```

后续 `t…t+7` 的 128 条无 hint 回报用于难度奖励，不能替代换题时的无 hint 回报计算 regret。否则会混入 solver 后续能力变化。

### 6.2 奖励混合

```text
p = mean(all 128 plain returns for this environment)
difficulty = plateau(p; band=[0.4,0.6], ramp=0.25)
raw_generator_reward = 0.4 * regret_norm + 0.6 * difficulty
```

plateau 形状以已锁定的实现为准：在目标带宽内为平顶，外侧按 ramp 衰减；独立检查者应从原始回报重新计算，不能仅读取程序打印的汇总。之后按技能组中心化一次，保留有效负优势；solver 按环境对 outcome 归一化一次。训练后端不得再归一化。

例：换题时 hint 均值 0.625、plain 均值 0.5，则 regret 为 0.125，归一化后约 0.8333；若完整窗口胜率为 0.5，difficulty=1，raw 奖励约 0.9333。后续胜率变化不会改写已冻结的 0.125 regret。这个例子是说明计算，不是实测结果。

### 6.3 环境和 hint 的合法性

生成的 Python 环境要通过语法、执行、多个 reset seed 和模型语义检查；准确留下接受或拒绝原因。检查 reset/step、工具 schema、工具参数、状态变更、终止奖励、随机 seed，以及 hint/play 两侧预算一致。Hint writer 能看环境源码，solver 不能直接看；hint 的作用不等于把源码或奖励答案发给 solver。

只重试被拒绝的固定技能/编号槽位；已接受的环境和生成轨迹保留。两侧 play 开始前必须具有完整 24 个有效环境和每技能 8 个。现有实施上限为每槽 80 次尝试、整段生成 3600 秒；这是本地有限重采样策略，并非论文公开参数。语义检查是模型自检，不构成所有状态可达性或可解性的形式化保证。

无效生成任务必须在优势归一化前排除，不能通过零奖励获得相对正优势。合法的失败或 TRUNCATED 轨迹可以保留；基础设施 TIMEOUT、缺轨迹和坏解析不能伪装成正常失败数据。

## 7. 必须先跑的测试和通过标准

完整修复项目中运行以下命令；路径应指向已核收并适配的项目。测试代码需从原复现项目迁移，**不在这个轻量交接仓库中**。

```bash
mkdir -p evidence/preflight
python check_paper_main_recipe.py --output evidence/preflight/main.json
python check_paper_hint_budget.py --output evidence/preflight/hint.json
python check_paper_logprob_protocol.py --output evidence/preflight/logprob.json
python check_paper_pool_integrity.py --output evidence/preflight/pool.json
python check_paper_runtime_state.py --output evidence/preflight/runtime.json
```

已有修复分别通过 10/7/4/7/16 项 CPU 控制，监控套件另有 28 项；独立检查额外运行 9 项顺序和负控。新机器必须重新运行，不继承这些通过结果。

| 阶段 | 必须验证 | 不通过时 |
|---|---|---|
| CPU 配方 | 400/24/16+16/8，原始回报能独立复算奖励，负样本保留 | 不提交完整训练 |
| Hint 调用 | 原生工具调用解析一致、归因正确、25 turns 预算一致 | 修复 parser 或归因，不能改奖励绕过 |
| 原始 logprob | SGLang 服务实际进程启用原始概率，温度不改变记录概率 | 不进行 PPO 更新 |
| 环境池 | 拒绝后补齐固定槽位；24 与 3×8；80/3600 限制生效 | 保留诊断，停止该轮 |
| 恢复 | 39→save/load→40 的 408 样本逐值、奖励和 RNG 一致；缺/坏 state 拒绝 | 不声称可完整恢复 |
| GPU 启动 | 四卡可见、NCCL、预加载 attention backward、RMSNorm、分块 logprob 正确 | 保留启动日志，先修运行时 |
| 实际首轮 | 384 条 actor、一次优化器更新、有限 loss/grad_norm、参数确实变化 | 启动成功不能代替该检查 |
| 第 8 轮 | 完整 128 plain/环境、冻结 16+16、24 生成器样本加入 408 batch | 检查延迟池与奖励时点 |
| 首个 39 检查点 | DCP+runtime 完整配对、模型全值有限、scheduler=15456 | 不能据此恢复或删旧点 |
| 最终 399 | 400 次更新编号无缺失/重复、累计154776、49成熟池、权重可导出 | 不作为完整400训练结果 |

关键 logprob 设置：采样仍为 0.6，但 PPO 记录的是 pre-temperature 分布 logprob。`SGLANG_RETURN_ORIGINAL_LOGPROB=true` 必须进入实际 Ray/SGLang 服务进程；不能只在父 shell 设置。现有 `0.5.12.post1` 还使用锁定的 sampler overlay 和服务启动前 guard；只设置变量、不迁移兼容修复及哈希，不能视为协议已成立。记录 `train_rollout_logprob_abs_diff`、TIS 和实际服务配置；仅凭差值“小”不能证明两侧概率一致。

生成器和 solver 共享模型及优化器。生成器奖励为零不等于生成器参数不变；混合批梯度不等于已经单独证明生成器能力提升。

## 8. 超时与检查点恢复：已有故障及修复

上一轮训练在完成 80 次更新后中断：换题后的 5 条无 hint 整段 episode 超过 300 秒，只返回 379/384。严格校验阻止了下一次更新；没有发现 OOM/NaN 的证据。这里的超时包括模型排队和多轮执行，不足以断言某个工具卡死。

修复设置有/无 hint 两侧相同的 **1800 秒整 episode 限时**；无 hint 时从获得 128 并发信号量后开始计时，不计信号量排队。原 turns/token/温度/奖励保持不变。若仍缺轨迹，必须停止，禁止补零、选择性丢弃或偷偷再采一条凑数。“379 succeeded”只是返回了轨迹，不是赢了379个任务。

旧第79号 DCP 的模型权重全量有限，模型、优化器和 Megatron 分片 RNG 均存在，但缺旧生成器 token/logprob/mask、完整课程回报窗口、memory/corpus 私有 RNG。因此**不能加载旧79后补320轮并称连续400复现**；新训练从原始 Instruct 初始化开始。

新的每40次更新检查点必须包含：

1. 模型、优化器、scheduler 和 Megatron RNG；所有 rank 同步保存完成。
2. `spade-runtime-state.json`：待成熟生成器完整 Sample、旧 logprob/mask、8×16 回报窗口、换题时 hint/plain、活动环境代码/元数据、记忆及 corpus 状态和私有 RNG、rollout CPU RNG。
3. schema、轮数、来源哈希、语料身份、所有者和路径校验；原子提交后才成为完整配对点。

只在新完整配对点审计通过后删除旧点；新 sidecar 缺失或损坏必须保留旧点。首39和最终399独立全量读取模型值，常规保留审计不等于所有优化器矩值全量扫描。

恢复前先检查未提交的未来环境、奖励和缓存，保留诊断并隔离，禁止当成已完成数据复用。当前恢复会拒绝覆盖已有同名诊断归档，不是无限自动重试。SGLang 请求采样流与 UUID 路由不承诺跨重启逐位一致；CPU state parity 也不能冒充真实4B断点恢复已经验证。当前没有自动恢复训练。

## 9. τ² 基线和最终模型的完全配对评测

用未训练 Instruct 模型跑基线，再用最终导出模型跑相同评测；两者的代码、数据、用户/评委模型、seed、parser 和预算一致。只允许 DeepSeek provider 替换，不能顺带换 vLLM、并发数或 token 预算。

| 参数 | 固定值 |
|---|---|
| 三域 / split | retail、telecom、airline / `base`，不截断 |
| 独立 trial | 每任务 4 次 |
| 任务和分母 | retail 114×4=456；telecom 114×4=456；airline 50×4=200；合计1112 |
| 最大交互步数 / 并发 | 200 / 48 |
| Actor | SGLang、Qwen tool parser、TP1/DP1、mem fraction 0.7 |
| Actor temperature/top_p/top_k | 0.0 / 0.8 / 20 |
| Actor 输出上限 | **16384**，不要误用训练阶段8192 |
| 用户模拟器 | 冻结的 `deepseek-flash` provider，temperature=0，输出上限2048，保留 reasoning 适配 |
| 自然语言评委 | 同一 DeepSeek provider、temperature=0，沿用作者未显式设输出 token cap 的行为 |
| Seed、max_errors及其他默认值 | 原历史 τ² 和作者配置默认值；逐项记录，不新增覆盖 |
| 标题指标 | 三域成功率的等权均值（macro），同时报告各域和 micro |

以上是现有已固定 provider ID，并非声称它永远是 DeepSeek 当前最强模型。换 provider/model ID 后必须重新跑匹配基线，另标实验版本；不能直接与旧基线相减。

API 内部请求重试与额外重跑整个 episode 是不同层级。完整评测必须有1112个唯一 `(task_id, trial)`，不额外重跑失败 episode，不按剩余成功请求缩小分母。模型导致的 `too_many_errors` 保留原生终止与计分；基础设施错误单独标注。任务和 split 文件需核对历史 blob，作者真实私有运行的精确 benchmark SHA 未公开，不能宣称已恢复它。

已有完整基线：

| 指标 | 本地基线 | 论文原始4B基线 |
|---|---:|---:|
| Retail | 191/456 = 41.89% | 43.0% |
| Airline | 68/200 = 34.00% | 32.0% |
| Telecom | 192/456 = 42.11% | 18.0% |
| Macro | 39.33% | 31.0% |

原生计分保留了2个基础设施错误；完整任务集合和固定分母已核对。Telecom差异明显，不能全部归因于DeepSeek，也不能说数值对齐论文。论文训练后4B为 retail47.2%、airline35.6%、telecom21.5%、macro34.8%。本轮训练收益应相对自己的39.33%匹配基线计算，不能用论文31%制造提升。换机器、运行时或 provider 后应重新测基线。

## 10. 监控、时间和最终交付

每600秒核对调度器状态、训练进程、真实更新编号、当前阶段、GPU占用、梯度/概率指标、最新完整检查点、sidecar、奖励测量和保存审计。监控应与训练进程分离，检查点审计只用CPU。训练结束后按“最终399完整审计→HF导出→τ²评测→独立汇总”触发。

现有服务器的新四卡训练已重新启动，2026-10-10约23:46观察到首轮参数更新正在执行；这不是首轮完成或最终成功证明。此状态会过期，新机器开始前应重新检查。上一轮80次更新用时约6小时40分，线性外推400次约33小时；新超时设置、生成环境难度、负载和保存开销可能改变速度。正式 ETA 应使用至少两个完整8轮周期，并包含换题、hint和保存开销，不能按单个短轮估计。

执行者返回以下报告：

```markdown
# SPADE 复现检查报告
- 检查时间、机器和GPU：
- 代码提交/补丁及实际源码SHA；依赖/容器指纹：
- 原始模型与语料身份；是否重新初始化：
- 五类CPU检查、监控负控、GPU启动检查结果：
- 实际400/24/16+16/8配方和允许差异：
- 当前更新编号、有效环境、384/408 batch、scheduler累计样本：
- Hint/plain冻结时点、原始回报、独立奖励复算：
- 首39/最终399成对检查点及权重/恢复检查范围：
- 最近异常、原因证据、哪些恢复状态缺失：
- 完整周期耗时与ETA范围：
- 基线与最终模型的三域/macro/micro、1112唯一trial和错误数：
- 是否证明完整训练、配对收益；仍未验证或未公开的细节：
```

公开仓库只保存说明、核收代码、脱敏配置和必要来源指纹。模型、语料、生成任务/对话、服务密钥、私有路径和完整服务器日志留在个人机器，不提交 GitHub。
