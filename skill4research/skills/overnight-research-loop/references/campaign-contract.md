# 通用约定、证据与角色状态

按领域裁剪，不适用标 N/A；不要求所有任务有 GPU、模型、benchmark 或固定门槛。目的、时限/预算、可执行动作、评价依据、角色和持久位置应明确。null 示例不是授权。

```json
{
  "campaign_id": "project-date-name",
  "contract_revision": 1,
  "mode": "design-or-execute",
  "objective": null,
  "timezone": null,
  "deadline": null,
  "resources": {"environment": null, "allocation": null, "budget_limits": {}, "authorized_actions": []},
  "evaluation": {"protocol_revision": null, "baseline_reference": null, "experimental_units": null, "selection_policy": null, "promotion_criteria": null, "confirmation_policy": null, "cost_limits": {}},
  "orchestration": {"available_slots": null, "roster": [], "active_assignments": [], "open_challenges": [], "pending_acknowledgements": []},
  "runtime": {"supervision_interval": null, "feedback_ack_deadline": null, "continuation_backend": null, "last_heartbeat": null},
  "stage": "prepare",
  "active_runs": [],
  "next_action": null,
  "spent": {},
  "stop_reason": null
}
```

模型、数据、设备、候选、抽样、门槛写当前 protocol，不硬编码每晚设置。核实已有约定，不重复询问，不假设扩大预算；授权范围内可提出并披露临时协议，未知统计量不当事实。

## 候选

hypotheses.jsonl：hypothesis_id、revision、parent_id、mechanism_family/signature、claim、sources、past_related_runs、key_difference、predictions、refutation_conditions、strongest_support/objection、cost_estimate、status、gate_review_id、open_challenges、reopen_conditions。

状态如 proposed / under-challenge / diagnostic-only / approved / running / supported / unsupported / abandoned / parked，均指具体版本。重要前提、机制或协议改变须新版本，不能沿用旧批准。

## 实验和批准

runs.jsonl：run_id、hypothesis/revision、plan/protocol revision、artifact hashes、approval ID、materials/data version、baseline reference、worker/job identity、start/end、status、exit/error、raw outputs、diagnostics、metrics、costs、next_action。

批准绑定候选、实现/协议和证据版本。派发重查 open_challenges；关键新证据使相关 approval invalidated，不误影响其他部分。

## 质询与回执

challenges.jsonl：challenge_id、author、targets、hypothesis/approval/run versions、issue、evidence_refs、scope、severity、suggested_action、resolution_conditions、response_refs、status、decision。

feedback.jsonl：message_id、challenge_id、sender、recipients、payload_path、version、sent_at、delivery_state、ack_state、ack_at、recipient_current_work、action_taken。未确认不等于同意，恢复补送重要未确认消息；工具无回执则标未核实。

decisions.md：支持与反对、各角色回应、新观测、改变的理由、决定、影响范围、下一动作。项目 lessons：来源、观测与解释分开、范围、未来检验、反例/重启条件、版本。

## 一致性与恢复

协调者单写全局状态，原子替换或项目事务；workers 单独写产物。先保存质询和相关暂停状态，再通知并派发依赖动作。动作失败记录实际状态，不能把打算发送写成已发送。

恢复先核对真实 artifact、job 与最新版本，再读未决质询、回执和有效批准。补登记结果，先查未知任务再重跑。报告包括成果、反证、多样性、把关修正、经验范围、成本、在途任务和下一动作。
