"""Deterministic Lab04 experiment runner. Python 3.10+, no third-party packages."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path

CONDITIONS = {"C0": (0,0,0), "C1": (.8,.6,.2), "C2": (1.2,.6,.2),
              "C3": (.8,.25,.2), "C4": (.8,.6,0)}
DT, DURATION = .05, 30.0
HERE = Path(__file__).resolve().parent

def load_controller(path):
    spec = importlib.util.spec_from_file_location("lab04_controller", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def load_contract(path):
    contract = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = {"phi_rad": (.20,.20,[.10,.45]), "stride_half_m": (.055,.010,[.040,.070])}
    for key, (baseline,gain,bounds) in expected.items():
        entry = contract["controlled_parameters"][key]
        if (entry["baseline"],entry["gain"],entry["bounds"]) != (baseline,gain,bounds):
            raise ValueError(f"Week03 mapping changed: {key}")
    fixed = contract["fixed_parameters"]
    if any(fixed.get(k) != v for k,v in {"alpha":1.10,"dt_s":.05,"lift_height_m":.03}.items()):
        raise ValueError("Week03 fixed parameters changed")
    return contract

def mapping(r, contract):
    if not math.isfinite(r) or not 0 <= r <= 1:
        raise ValueError("receptor output outside [0,1]")
    out = {}
    for key, m in contract["controlled_parameters"].items():
        out[key] = max(m["bounds"][0], min(m["bounds"][1], m["baseline"]+m["gain"]*r))
    return out

def stimulus_at(k, profile):
    # Integer indices avoid floating-point boundary ambiguity.
    if profile == "step": return float(200 <= k < 400)
    if profile == "zero": return 0.0
    if profile == "one": return 1.0
    if profile == "spike": return float(k == 200)
    if profile == "fault": return float("nan") if k == 300 else float(200 <= k < 400)
    raise ValueError(profile)

def simulate(controller, condition, profile="step", contract=None):
    contract = contract or load_contract(HERE/"handoff_contract.json")
    prod, clear, bind = CONDITIONS[condition]
    rows = [dict(time_s=0.0,input_time_s=0.0,stimulus=0.0,h=0.0,r=0.0,raw=0.0,
                 p=0.0,c=0.0,b=0.0,fault=0,upper_clamp=0,lower_clamp=0,
                 **mapping(0.0,contract))]
    h = 0.0
    for k in range(600):
        stimulus = stimulus_at(k,profile)
        if condition == "C0":
            valid = math.isfinite(stimulus) and 0 <= stimulus <= 1
            r = stimulus if valid else 0.0
            state = dict(h=None,r=r,raw=None,p=None,c=None,b=None,fault=int(not valid))
        else:
            state = controller.step(h,stimulus,DT,prod,clear,bind)
            for key in ("h","r","raw","p","c","b"):
                if not math.isfinite(state[key]): raise ValueError(f"nonfinite controller {key} at step {k}")
            if not 0 <= state["h"] <= 1: raise ValueError("H bounds violated")
            if state["fault"] not in (0,1): raise ValueError("fault must be 0 or 1")
            h = state["h"]
        raw = state["raw"]
        rows.append(dict(time_s=round((k+1)*DT,8),input_time_s=round(k*DT,8),
                         stimulus=stimulus,**state,upper_clamp=int(raw is not None and raw>1),
                         lower_clamp=int(raw is not None and raw<0),**mapping(state["r"],contract)))
    if condition == "C0":
        for key in ("h","raw","p","c","b"): rows[0][key] = None
    return rows

def metrics(rows, condition, profile):
    updated = rows[1:]
    # State-window [10,20] includes state at stimulus-off, before its first off update.
    on = [r for r in rows if 10 <= r["time_s"] <= 20]
    peak_r = max(r["r"] for r in on)
    def crossing(level):
        return next((r["time_s"] for r in on if r["r"] >= level),None)
    lo, hi = crossing(.1*peak_r), crossing(.9*peak_r)
    latency = crossing(.1)
    recover = next((r["time_s"]-20 for r in rows
                    if r["time_s"]>=20 and r["r"] <= .1*peak_r),None)
    applicable = profile == "step" and peak_r > 0
    hormone = condition != "C0"
    return dict(condition=condition,profile=profile,
        peak_h=max(r["h"] for r in rows) if hormone else None,
        peak_r=max(r["r"] for r in rows),
        auc_h_left=sum(r["h"] for r in rows[:-1])*DT if hormone else None,
        latency_s=latency-10 if applicable and latency is not None else None,
        rise_10_90_s=hi-lo if applicable and lo is not None and hi is not None else None,
        recovery_s=recover if applicable else None,
        upper_clamp_fraction=sum(r["upper_clamp"] for r in updated)/600 if hormone else None,
        lower_clamp_fraction=sum(r["lower_clamp"] for r in updated)/600 if hormone else None,
        phi_total_variation_rad=sum(abs(b["phi_rad"]-a["phi_rad"]) for a,b in zip(rows,rows[1:])),
        stride_total_variation_m=sum(abs(b["stride_half_m"]-a["stride_half_m"]) for a,b in zip(rows,rows[1:])),
        fault_count=sum(r["fault"] for r in updated),
        na_reason="C0 has no H; non-step profiles have no step-response timing metrics; recovery may exceed trial")

def svg_plot(traces,key,title,unit,max_y,profile="step"):
    colors = ["#667085","#137d8e","#c06a22","#76538e","#315f91"]
    start,width = {"step":(370,300),"fault":(370,300),"one":(70,900),"zero":(70,0),"spike":(370,1.5)}[profile]
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 360" role="img" aria-label="{title}">',
              '<rect width="1000" height="360" fill="white"/>',
              f'<rect x="{start}" y="35" width="{width}" height="260" fill="#eef6f7"/>',
              f'<text x="70" y="22" font-size="18">{title} ({unit})</text>']
    for i in range(6):
        y=295-i*52
        pieces.append(f'<path d="M70 {y} H970" stroke="#ddd"/><text x="8" y="{y+5}" font-size="14">{i*max_y/5:.3g}</text>')
    for t in range(0,31,5):
        x=70+t*30
        pieces.append(f'<text x="{x-8}" y="318" font-size="14">{t}</text>')
    for (condition,rows),color in zip(traces.items(),colors):
        points=" ".join(f'{70+r["time_s"]*30:.2f},{295-r[key]/max_y*260:.2f}' for r in rows if r[key] is not None)
        pieces.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2.4"/>')
        index=list(traces).index(condition)
        pieces.append(f'<text x="{80+index*170}" y="345" fill="{color}" font-size="16">{condition}</text>')
    pieces.append('<text x="880" y="318" font-size="14">time (s)</text></svg>')
    return "".join(pieces)

def run(args):
    out=Path(args.output_dir)
    if out.exists() and any(out.iterdir()) and not args.overwrite:
        raise FileExistsError("Output directory is not empty. Choose a new directory or explicitly use --overwrite.")
    out.mkdir(parents=True,exist_ok=True)
    contract=load_contract(args.contract)
    source=Path(args.student_file) if args.controller_source=="student" else HERE/"reference_controller.py"
    controller=load_controller(source)
    conditions=list(CONDITIONS) if args.condition=="all" else [args.condition]
    traces={c:simulate(controller,c,args.profile,contract) for c in conditions}
    results=[metrics(rows,c,args.profile) for c,rows in traces.items()]
    for c,rows in traces.items():
        with (out/f"{c}_{args.profile}.csv").open("w",newline="",encoding="utf-8") as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    (out/"metrics.json").write_text(json.dumps(results,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    with (out/"metrics.csv").open("w",newline="",encoding="utf-8-sig") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(results[0])); writer.writeheader(); writer.writerows(results)
    config=dict(model="proposed course model",dt_s=DT,duration_s=DURATION,h0=0,conditions={c:CONDITIONS[c] for c in conditions},
                profile=args.profile,controller_source=args.controller_source,
                controller_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),contract=contract,
                time_alignment="row 0 initial; row k+1 = state after input interval [k*dt,(k+1)*dt)",
                auc_definition="left rectangle sum H(t_k)*dt for k=0..599; [0,30)")
    (out/"config.json").write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding="utf-8")
    plot_files=[]
    for key,title,unit,max_y in [("h","Hormone H","normalized",1.1),("r","Receptor R","normalized",1.1),
                                  ("phi_rad","Bounded phi","rad",.45),("stride_half_m","Bounded stride half","m",.07)]:
        filename=f"{key}.svg"; plot_files.append(filename)
        (out/filename).write_text(svg_plot(traces,key,title,unit,max_y,args.profile),encoding="utf-8")
    def fmt(x): return "N/A" if x is None else (f"{x:.4f}" if isinstance(x,float) else str(x))
    columns=["condition","peak_h","auc_h_left","latency_s","rise_10_90_s","recovery_s","upper_clamp_fraction","phi_total_variation_rad"]
    table="<tr>"+"".join(f"<th>{k}</th>" for k in columns)+"</tr>"+"".join("<tr>"+"".join(f"<td>{fmt(r[k])}</td>" for k in columns)+"</tr>" for r in results)
    html='<!doctype html><html lang="th"><meta charset="utf-8"><title>Lab04 results</title><style>body{font:18px Tahoma,sans-serif;margin:35px;background:#f6f8fa;color:#20313a}main{max-width:1100px;margin:auto}img{width:100%;background:white}table{border-collapse:collapse;font-size:14px}td,th{padding:10px;border:1px solid #ccc}section{margin:25px 0}</style><main><h1>Lab04: ผลการจำลอง Artificial Hormone</h1><p>proposed course model • พื้นหลังสีอ่อนคือ stimulus-on 10–20 s (ใช้เฉพาะ profile step) • กราฟยังไม่ยืนยัน gait หรือความปลอดภัยของหุ่นยนต์จริง</p><p>อ่าน S จาก CSV แล้วตรวจ P−C−B: ผลสุทธิบวกทำให้ H เพิ่ม ผลสุทธิลบทำให้ H ลด จากนั้น R แปลง H เป็นคำสั่ง phi และ stride</p><table>'+table+'</table>'+''.join(f'<section><img src="{file}" alt="{file}"></section>' for file in plot_files)+'<p>N/A หมายถึงใช้ไม่ได้หรือไม่พบ crossing ภายใน trial ดูนิยามใน README และ config.json</p></main></html>'
    (out/"report.html").write_text(html,encoding="utf-8")
    print(json.dumps(dict(output=str(out),rows_per_condition=601,metrics=results),ensure_ascii=False,indent=2,allow_nan=False))

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controller-source",choices=["student","reference"],default="student")
    parser.add_argument("--student-file",default=str(HERE/"student_hormone.py"))
    parser.add_argument("--condition",choices=["all",*CONDITIONS],default="all")
    parser.add_argument("--profile",choices=["step","zero","one","spike","fault"],default="step")
    parser.add_argument("--contract",default=str(HERE/"handoff_contract.json"))
    parser.add_argument("--output-dir",default="results/comparison")
    parser.add_argument("--overwrite",action="store_true",help="Explicitly replace files in an existing experiment output directory")
    run(parser.parse_args())
