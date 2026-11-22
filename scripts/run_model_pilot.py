"""Six-slot IN02 cloud-model pilot. Default is offline check; execution needs group approval."""
import argparse
import base64
import hashlib
import json
import os
import platform
import re
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from voice_agent.data.development import load_development, case_pack
from voice_agent.data.preprocess import chunk_knowledge
from voice_agent.evaluation.evaluator import expected_state, transcript_text, diff
from voice_agent.evaluation.measurement import count_rate, nearest_rank, repetition_summary
from voice_agent.inference.retrieval import BM25Index
from voice_agent.models.budget import CostLedger, _usage_cost
from voice_agent.models.llm import OpenAICompatibleClient
from voice_agent.pipelines.episode import run_episode
from voice_agent.utils.common import load_env, write_json

GROUP = "step12_model_pilot_001"
OPENAI = "gpt-4o-mini-2024-07-18"
GEMMA = "google/gemma-4-26b-a4b-it:free"
SETTINGS = ROOT / "milestones/M4_training/model_pilot_settings.json"
EVIDENCE = ROOT / "milestones/M4_training/evidence/step12_planning"
LEDGER = ROOT / "experiments/cost_ledger.json"
LIMITS = dict(max_retries=0, max_caller_turns=12, max_tool_steps=8,
              max_audio_seconds=0, max_request_bytes=64000)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan():
    manifest, _, _ = load_development()
    files = set((ROOT/"src/voice_agent").rglob("*.py")) | set((ROOT/"scripts").glob("*.py"))
    files |= {ROOT/"milestones/M4_training/development"/f for f in ["manifest.json",*manifest["file_sha256"]]}
    files |= {EVIDENCE/f for f in ("scope-decision.json","openrouter-public-models.json","gemma-endpoints.json")}
    files |= {ROOT/"milestones/M4_training/model_pilot_plan.md"}
    slots=[];batches=[]
    for repetition in (1,2,3):
        order=("gemma","openai") if repetition%2 else ("openai","gemma")
        for candidate in order:
            sid=f"{GROUP}_r{repetition}_{candidate}"
            slots.append(dict(id=sid,scenario_id="IN02",repetition=repetition,candidate=candidate,
                              agent_batch=sid+"_agent",evaluation_batch=sid+"_eval"))
            for kind,model,n,cap,cost in [("agent",GEMMA if candidate=="gemma" else OPENAI,96,800,
                                         "0" if candidate=="gemma" else "1.88928"),
                                        ("eval",OPENAI,13,1200,"0.25176")]:
                batches.append(dict(id=sid+"_"+kind,allocation="text_development",model=model,
                    max_cost_usd=cost,limits={**LIMITS,"max_requests":n,"max_output_tokens":cap},requests=[]))
    return dict(version="m4-cloud-model-pilot-v1",machine_scorer_version="m4-pilot-machine-v1",
        group_id=GROUP,requires_explicit_group_approval=True,
        scope="Approved scope reduction: IN02 only, three repetitions/candidate, six slots; not full Step12",
        architecture="unchanged SingleAgent",documents="frozen short",retrieval="BM25 k3 facts; rules in system prompt",
        caller_and_judge=OPENAI,agent_models={"openai":OPENAI,"gemma":GEMMA},
        temperatures=0,agent_output_cap=800,caller_output_cap=200,judge_output_cap=1200,
        limits=LIMITS,pooled_agent_requests_per_caller_turn=8,timeout_seconds=30,concurrency=1,
        slots=slots,batches=batches,max_openai_cost_usd="7.17840",max_openrouter_cost_usd="0",
        openrouter_routing="only google-ai-studio, no fallbacks, require parameters, zero max token prices, data_collection deny, no BYOK",
        runtime=dict(python=platform.python_version(),system=platform.system(),machine=platform.machine()),
        source_sha256={str(f.relative_to(ROOT)):sha(f) for f in sorted(files)},
        analysis="N=1 independent scenario; report six attempts, triplet consistency, machine labels separately from human-pending audits; no significance or broad model selection",
        continuation="no scenario/model replacement or retry; halt group on infrastructure/judge/simulator issue or source drift; do not auto-start steps13/14")


def check():
    raw=SETTINGS.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SETTINGS.with_suffix(".sha256").read_text().strip():
        raise ValueError("Pilot settings checksum differs")
    value=json.loads(raw)
    if json.dumps(value,sort_keys=True)!=json.dumps(plan(),sort_keys=True):
        raise ValueError("Pilot source/runtime/settings drift")
    return value


def safe(value, secrets):
    if isinstance(value,bytes):
        for secret in secrets:
            if secret:value=value.replace(secret.encode(),b"[REDACTED]")
        try:value=value.decode("utf-8")
        except UnicodeDecodeError:return {"encoding":"base64","body":base64.b64encode(value).decode("ascii")}
    if isinstance(value,str):
        for secret in secrets:
            if secret:value=value.replace(secret,"[REDACTED]")
        return re.sub(r"\bsk-[A-Za-z0-9_.*-]+","[REDACTED]",value)
    if isinstance(value,list):return [safe(v,secrets) for v in value]
    if isinstance(value,dict):return {k:safe(v,secrets) for k,v in value.items()}
    return value


def journal_at(out,secrets):
    records={}
    def journal(event):
        rid=event["request_id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]+",rid):raise ValueError("Invalid journal ID")
        records.setdefault(rid,[]).append(safe({**event,"observed_at_utc":datetime.now(timezone.utc).isoformat(),
                                               "monotonic_ns":time.perf_counter_ns()},secrets))
        write_json(out/"calls"/(rid+".json"),{"events":records[rid]})
    return journal


def validate_approval(approval):
    if (approval.get("approved") is not True or approval.get("group_id")!=GROUP
            or approval.get("settings_sha256")!=sha(SETTINGS)
            or approval.get("max_openai_cost_usd")!="7.17840"
            or approval.get("max_openrouter_cost_usd")!="0"
            or not isinstance(approval.get("user_reply"),str) or not approval["user_reply"].strip()):
        raise ValueError("Missing or mismatched explicit group approval")


def register(value,approval):
    validate_approval(approval)
    budget=CostLedger(LEDGER,value["batches"][0]["id"])
    with budget._locked():
        data=json.loads(LEDGER.read_text())
        if any(b["id"] in {x["id"] for x in value["batches"]} for b in data["batches"]):
            raise ValueError("Pilot already registered; no reruns")
        if (any(b.get("halted") for b in data["batches"])
                or any(r["status"]!="reconciled" for b in data["batches"] for r in b["requests"])):
            raise ValueError("Unresolved ledger requests or halted batch")
        prices=data["models"][OPENAI]
        if (prices["input_usd_per_million"],prices["output_usd_per_million"],prices["max_input_tokens"])!=("0.15","0.60",128000):
            raise ValueError("OpenAI price/context differs from approved bounds")
        # Current registration is allowed only before any text-development spending.
        if any(b["allocation"]=="text_development" for b in data["batches"]):
            raise ValueError("Prior text batches need a reviewed aggregate budget amendment")
        if Decimal(data["allocations"]["text_development"])<Decimal("7.17840"):
            raise ValueError("Insufficient text allocation")
        _,_,total=budget._totals(data,Decimal(data["starting_credit_usd"]))
        if total+Decimal("7.17840")>Decimal(data["starting_credit_usd"]):
            raise ValueError("Insufficient global credit estimate")
        if GEMMA in data["models"]:raise ValueError("Unexpected existing Gemma catalog entry")
        data["models"][GEMMA]=dict(provider="openrouter_free",no_charge_only=True,
            input_usd_per_million="0",output_usd_per_million="0",max_input_tokens=262144,
            documented_max_output_tokens=32768,source="Step12 pinned public catalog/endpoints; zero-price only")
        for batch in value["batches"]:
            data["batches"].append({**batch,"approved":True,"approval_reference":approval["approval_reference"],
                "approval_group":GROUP,"approved_at_utc":datetime.now(timezone.utc).isoformat()})
        if sum(Decimal(b["max_cost_usd"]) for b in value["batches"])!=Decimal("7.17840"):
            raise ValueError("Sub-batch ceilings do not match group approval")
        budget._save(data)


def report(records):
    result={"planned_attempts":6,"recorded_attempts":len(records),"independent_scenarios":1,
            "human_review":"pending; machine rubric is not reviewed strict completion or factual accuracy",
            "common_model_selection":"pending; one-case pilot cannot establish broad superiority","candidates":{}}
    for candidate in ("openai","gemma"):
        rows=[r for r in records if r["candidate"]==candidate]
        scores=[bool(r["result"]["reward"]) if r["result"]["reward"] is not None else None for r in rows]
        scores += [None]*(3-len(scores))
        db=[r["result"]["db_pass"] for r in rows]+[None]*(3-len(rows))
        comp=[r["result"]["safety_pass"] for r in rows]+[None]*(3-len(rows))
        repetitions=[dict(scenario_id="IN02",repetition=r["repetition"],strict_success=bool(r["result"]["reward"]) if r["result"]["reward"] is not None else None) for r in rows]
        latency=[r["result"]["usage"]["agent"]["latency_s"] for r in rows
                 if r["result"]["usage"]["agent"]["llm_calls"]>0]
        result["candidates"][candidate]=dict(machine_task_success=count_rate(scores),crm_exact=count_rate(db),
            machine_policy_compliance=count_rate(comp),machine_triplet=repetition_summary(repetitions,["IN02"]),
            agent_total_request_seconds=latency,agent_total_seconds_p50=nearest_rank(latency,.5),
            factual_accuracy=None,reviewed_strict_completion=None,voice_latency=None,
            missing_metrics_reason="reviewed claims/action/coverage annotations absent; no audio",statuses=[r["result"]["status"] for r in rows])
    return result


def cost_report():
    data=json.loads(LEDGER.read_text());attempts={}
    for batch in data["batches"]:
        if batch.get("approval_group")!=GROUP:continue
        aid=batch["id"].rsplit("_",1)[0]
        row=attempts.setdefault(aid,{"observed_service_estimate_usd":Decimal(0),
            "observed_evaluation_estimate_usd":Decimal(0),"requests":0,"unknown_requests":0,"role_counts":{},"request_ids":[]})
        for request in batch["requests"]:
            row["requests"]+=1
            row["request_ids"].append(request["id"])
            role=request["role"];row["role_counts"][role]=row["role_counts"].get(role,0)+1
            if request["status"]!="reconciled":row["unknown_requests"]+=1;continue
            amount=_usage_cost(request["usage"],data["models"][batch["model"]],request["max_output_tokens"])
            key="observed_service_estimate_usd" if role=="AGENT" else "observed_evaluation_estimate_usd"
            row[key]+=amount
    for row in attempts.values():
        for key in ("observed_service_estimate_usd","observed_evaluation_estimate_usd"):row[key]=str(row[key])
    return {"by_attempt":attempts,"basis":"usage-priced estimate; raw free responses must show zero cost; not invoice or pooled OpenRouter credit",
            "cost_per_call_minute":None}


def execute(approval_path):
    value=check();load_env()
    secrets=[os.getenv("OPENAI_API_KEY",""),os.getenv("OPENROUTER_API_KEY","")]
    if not all(secrets):raise ValueError("Required keys absent")
    approval=json.loads(approval_path.read_text());approval["approval_reference"]=str(approval_path.relative_to(ROOT))
    validate_approval(approval)
    out=ROOT/"experiments/runs"/GROUP
    if out.exists():raise FileExistsError("Pilot output exists; preserve interrupted attempt")
    if approval.get("settings_sha256")!=sha(SETTINGS):raise ValueError("Approval settings mismatch")
    out.mkdir(parents=True,exist_ok=False)
    write_json(out/"approval.json",approval)
    write_json(out/"manifest.json",value)
    register(value,approval)
    from voice_agent.models.openrouter_free import FreeOpenRouterClient
    _,tasks,packs=load_development();task=next(t for t in tasks if t["id"]=="IN02")
    records=[];disposition="running"
    def save():
        write_json(out/"results.json",safe({"disposition":disposition,"summary":report(records),
            "costs":cost_report(),"records":records},secrets))
    save()
    try:
        for slot in value["slots"]:
            check()
            attempt=out/slot["id"];attempt.mkdir(exist_ok=False)
            pack=case_pack(task,packs);chunks=chunk_knowledge(pack)
            index=BM25Index([c for c in chunks if c["kind"]=="sourced_fact"])
            write_json(attempt/"initial_expected.json",{"initial":pack.seed,"expected":expected_state(pack.seed,task["gold"]),"chunks":chunks})
            write_json(attempt/"status.json",{"status":"started","slot":slot,"at_utc":datetime.now(timezone.utc).isoformat(),
                "timing_conditions":{"host":platform.platform(),"load_average":os.getloadavg(),"concurrency":1,"provider_warmth":"unknown; no unapproved warmup","network_region":"not verified"}})
            journal=journal_at(attempt,secrets)
            agent_budget=CostLedger(LEDGER,slot["agent_batch"]);eval_budget=CostLedger(LEDGER,slot["evaluation_batch"])
            if slot["candidate"]=="openai":
                agent=OpenAICompatibleClient(OPENAI,"https://api.openai.com/v1",secrets[0],budget=agent_budget,role="AGENT",journal=journal)
            else:agent=FreeOpenRouterClient(api_key=secrets[1],budget=agent_budget,journal=journal)
            clients={"agent":agent,**{name:OpenAICompatibleClient(OPENAI,"https://api.openai.com/v1",secrets[0],
                budget=eval_budget,role=role,journal=journal) for name,role in (("simulator","SIMULATOR"),("judge","JUDGE"))}}
            def checkpoint(event):
                path=attempt/"tool_states"/f"{len(event['tool_log']):03d}.json"
                if path.exists():raise FileExistsError("Tool checkpoint would overwrite evidence")
                write_json(path,safe(event,secrets))
            outcome=run_episode(task,pack,"llm",clients,chunks,index,checkpoint=checkpoint,stop_on_protocol_issue=True)
            record={**slot,"result":outcome};records.append(record)
            write_json(attempt/"result.json",safe(record,secrets))
            write_json(attempt/"crm_diff.json",diff(expected_state(pack.seed,task["gold"]),outcome["final_state"]))
            (attempt/"transcript.txt").write_text(safe(transcript_text(outcome["turns"],full_tool_results=True),secrets)+"\n")
            write_json(attempt/"human_review.json",{"status":"pending","coverage_valid":None,"strict_task_success":None,
                "policy_compliant":None,"spurious_writes":None,"wrong_record":None,"duplicate_lead":None,
                "unconfirmed_actions":None,"claims_complete":False,"factual_claims":[],"reviewer":None})
            write_json(attempt/"status.json",{"status":"recorded","episode_status":outcome["status"],"at_utc":datetime.now(timezone.utc).isoformat()})
            save()
            if (outcome["judge_status"]!="valid" or outcome["status"]!="completed"
                    or any(i["category"] in ("infrastructure","simulator","judge") for i in outcome["issues"])):
                disposition="stopped_requires_review";break
        else:disposition="complete_pending_human_review"
    except Exception as error:
        disposition="interrupted_requires_review"
        write_json(out/"interruption.json",safe({"error_type":type(error).__name__,"error":str(error)},secrets))
    finally:
        save()
    print(json.dumps({"disposition":disposition,"recorded_attempts":len(records),"artifact":str(out.relative_to(ROOT))},indent=2))
    return 0 if disposition=="complete_pending_human_review" else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze",action="store_true")
    parser.add_argument("--execute",action="store_true")
    parser.add_argument("--approval",type=Path)
    args=parser.parse_args()
    if args.freeze and args.execute:parser.error("Freeze and execute are separate actions")
    if args.freeze:
        if SETTINGS.exists() or SETTINGS.with_suffix(".sha256").exists():raise FileExistsError("Pilot freeze exists")
        with SETTINGS.open("x") as f:f.write(json.dumps(plan(),indent=2)+"\n")
        with SETTINGS.with_suffix(".sha256").open("x") as f:f.write(sha(SETTINGS)+"\n")
    if args.execute:
        if not args.approval:parser.error("Explicit group approval file required")
        sys.exit(execute(args.approval.resolve()))
    value=check()
    print(json.dumps({"integrity":"pass","group":GROUP,"attempts":6,"max_openai_cost_usd":value["max_openai_cost_usd"],"max_openrouter_cost_usd":"0","execution_approved":False},indent=2))


if __name__=="__main__":main()
