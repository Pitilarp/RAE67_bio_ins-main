"""Run a synthetic seven-topic transport experiment using Python stdlib only."""
import argparse
from collections import Counter
import csv
from dataclasses import asdict
import hashlib
import html
import json
import math
from pathlib import Path
import random
import shutil
import statistics
from lamp_week07.bridge import Engine, TOPICS, load_policy
from lamp_week07.course_model import Config, Frame, protocol

PRIMARY = ('button_01','touch_01','approach_01','clear_01','near_01','clear_02','button_02')

def write_csv(path, rows):
    with Path(path).open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ['empty'])
        writer.writeheader()
        writer.writerows(rows)

def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')

def run_trial(transition, condition='C0', seed=41, config=Config(), replay=None):
    frames = protocol(config, seed)
    rng, pending, trace, commands = random.Random(seed+7000), [], [], []
    engine = Engine(transition, config)
    latest = {c: {'value': 0. if c != 'distance' else 1.2, 'sample': -1., 'source': 0., 'id': '', 'seq': -1} for c in ('button','touch','distance')}
    source_inputs, delivered_ages = {}, []
    counts = Counter()
    replay_map = {(int(x['sequence']), x['channel']): x for x in replay} if replay is not None else None
    for sequence, original in enumerate(frames):
        t = original.time_s
        for channel in latest:
            value = getattr(original, 'distance_m' if channel == 'distance' else channel)
            sample, source = getattr(original, channel+'_sample_s'), getattr(original, channel+'_source_s')
            input_id = getattr(original, channel+'_input_id')
            if replay_map is not None:
                saved = replay_map[sequence, channel]
                value=float(saved['value']); sample=float(saved['sample_time_s']); source=float(saved['source_time_s']); input_id=saved['input_id']
                if abs(float(saved['publish_time_s'])-t)>1e-9: raise ValueError('Replay publish times must match the fixed dt grid')
            if input_id and input_id not in source_inputs:
                kind = 'fault' if input_id.startswith(('invalid', 'stale')) else channel if channel != 'distance' else original.expected_event
                source_inputs[input_id] = {'input_id': input_id, 'kind': kind, 'source_time_s': source, 'primary_expected_both': input_id in PRIMARY}
            if replay_map is not None:
                saved = replay_map[sequence, channel]
                dropped = saved['transport_dropped'] == 'True'
                delay = float(saved['planned_delay_s'])
                if saved['transport_dropped'] not in ('True','False') or not math.isfinite(delay) or delay<0: raise ValueError('Invalid replay transport metadata')
            else:
                dropped = condition == 'C1' and (rng.random() < .08 or (12.5 <= t < 12.7))
                delay = 0. if condition == 'C0' else rng.choice((0., .02, .04, .06, .10, .14, .18))
            receipt = round(t+delay,8)
            row = {'sequence':sequence, 'channel':channel, 'topic':'/lamp/input/'+channel,
                   'type': TOPICS['/lamp/input/'+channel][0], 'value': value,
                   'source_time_s': source, 'sample_time_s': sample, 'publish_time_s': t,
                   'planned_delay_s':delay, 'planned_receipt_s':receipt,
                   'transport_dropped': dropped, 'status':'dropped' if dropped else 'queued',
                   'receipt_time_s':None, 'transport_age_s':None, 'input_id':input_id}
            trace.append(row)
            counts['published'] += 1
            if dropped: counts['transport_dropped'] += 1
            else: pending.append((receipt,sequence,channel,value,sample,source,input_id,row))
        due = sorted((job for job in pending if job[0] <= t+1e-9), key=lambda job:(job[0],job[1],job[2]))
        pending = [job for job in pending if job[0] > t+1e-9]
        for _, seq, channel, value, sample, source, input_id, row in due:
            row['receipt_time_s'], row['transport_age_s'] = t, round(t-row['publish_time_s'],8)
            delivered_ages.append(row['transport_age_s'])
            counts['received'] += 1
            if seq <= latest[channel]['seq']:
                row['status'] = 'discarded_out_of_order'
                counts['out_of_order'] += 1
            else:
                row['status'] = 'accepted'
                counts['accepted'] += 1
                latest[channel] = {'value':value,'sample':sample,'source':source,'id':input_id,'seq':seq}
        frame = Frame(t,latest['button']['value'],latest['touch']['value'],latest['distance']['value'],
                      latest['button']['sample'],latest['touch']['sample'],latest['distance']['sample'],
                      latest['button']['source'],latest['touch']['source'],latest['distance']['source'],
                      latest['button']['id'],latest['touch']['id'],latest['distance']['id'])
        command = engine.step(frame)
        commands.append(command)
    for job in pending:
        job[-1]['status'] = 'censored_after_trial'
        counts['censored'] += 1
    event_rows = engine.event_rows()
    outcomes = []
    for source in source_inputs.values():
        candidates = [e for e in event_rows if e['input_id']==source['input_id'] and e['kind']==source['kind']]
        motion = min((e['first_motion_s'] for e in candidates if e['first_motion_s'] is not None),default=None)
        rgb = min((e['first_rgb_s'] for e in candidates if e['first_rgb_s'] is not None),default=None)
        both = max(motion,rgb) if motion is not None and rgb is not None else None
        latency = None if both is None else round(both-source['source_time_s'],8)
        outcomes.append({**source,'recognized_count':len(candidates), 'first_motion_s':motion, 'first_rgb_s':rgb,
                         'both_latency_s':latency,'pass_1s_both':None if latency is None else latency<=1.+1e-9})
    primary = [x for x in outcomes if x['primary_expected_both']]
    observed = [x['both_latency_s'] for x in primary if x['both_latency_s'] is not None]
    metrics = {'condition':condition,'seed':seed,'published':counts['published'],'received':counts['received'],
               'accepted':counts['accepted'],'transport_dropped':counts['transport_dropped'],
               'discarded_out_of_order':counts['out_of_order'],'censored_after_trial':counts['censored'],
               'mean_transport_age_s':statistics.mean(delivered_ages) if delivered_ages else None,
               'max_transport_age_s':max(delivered_ages,default=None),
               'fault_ticks':sum(bool(x['fault_channels']) for x in commands),'total_ticks':len(commands),
               'state_transitions':sum(a['emotion']!=b['emotion'] for a,b in zip(commands,commands[1:])),
               'primary_expected_count':len(primary),'primary_missing_both_count':sum(x['both_latency_s'] is None for x in primary),
               'primary_pass_1s_both_count':sum(x['pass_1s_both'] is True for x in primary),
               'primary_median_both_latency_s':statistics.median(observed) if observed else None,
               'primary_max_both_latency_s':max(observed,default=None),'source_outcomes':outcomes,
               'measurement_scope':'virtual synthetic transport and applied command onset; ROS/DDS and hardware not measured',
               'fault_interpretation':'invalid values OR acquisition sample age>0.12s; both conditions include shared Lab06 invalid/stale probes',
               'latency_denominator':'all10source inputs retained; baseline primary7 predeclared; misses retained, not zero',
               'group_policy':'predeclare own expected subset before runs and recompute from source_outcomes identically in both conditions'}
    return trace, commands, event_rows, metrics

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy-file',default=str(Path(__file__).parent/'lamp_week07/student_policy.py'))
    parser.add_argument('--condition',choices=('C0','C1','all'),default='all')
    parser.add_argument('--repeats',type=int,default=3)
    parser.add_argument('--output-dir',default='results/my_run')
    parser.add_argument('--replay',help='Replay one previous input_trace.csv transport schedule; repeats must=1, condition C0/C1')
    args = parser.parse_args()
    if args.repeats<1: parser.error('repeats must be positive')
    if args.replay and (args.repeats!=1 or args.condition=='all'): parser.error('replay requires --repeats 1 and one condition')
    policy = Path(args.policy_file).resolve()
    transition = load_policy(policy)
    out = Path(args.output_dir)
    if out.exists() and any(out.iterdir()): parser.error('output directory is not empty; choose a new path to preserve runs')
    out.mkdir(parents=True,exist_ok=True)
    snapshot = out/'source_snapshot'; snapshot.mkdir()
    shutil.copy2(policy,snapshot/'selected_policy.py')
    for source in (Path(__file__),Path(__file__).parent/'lamp_week07/bridge.py',Path(__file__).parent/'lamp_week07/course_model.py'):
        shutil.copy2(source,snapshot/source.name)
    replay_rows = None
    replay_seed = None
    if args.replay:
        with Path(args.replay).open(encoding='utf-8',newline='') as handle: replay_rows=list(csv.DictReader(handle))
        prior_config=json.loads(Path(args.replay).with_name('config.json').read_text(encoding='utf-8'))
        if prior_config['transport']['condition'] != args.condition: parser.error('replay condition must match recorded condition')
        replay_seed=prior_config['config']['seed']
        expected={(i,c) for i in range(1101) for c in ('button','touch','distance')}
        actual=[(int(r['sequence']),r['channel']) for r in replay_rows]
        if len(actual)!=len(expected) or set(actual)!=expected: parser.error('replay trace must contain exactly1101x3unique messages')
    summaries = []
    for repeat in range(1,args.repeats+1):
        for condition in ('C0','C1') if args.condition=='all' else (args.condition,):
            seed = replay_seed if replay_seed is not None else 40+repeat
            folder=out/f'{condition}_r{repeat:02}'; folder.mkdir()
            cfg=Config(seed=seed)
            trace,commands,events,metrics=run_trial(transition,condition,seed,cfg,replay_rows)
            metrics['repeat']=repeat
            write_csv(folder/'input_trace.csv',trace); write_csv(folder/'command_trace.csv',commands); write_csv(folder/'events.csv',events)
            write_json(folder/'metrics.json',metrics)
            write_json(folder/'config.json',{'provenance':'proposed course model','config':asdict(cfg),'topics':TOPICS,
                'transport': {'condition':condition,'drop_probability':0. if condition=='C0' else .08,'burst_drop_s':None if condition=='C0' else [12.5,12.7],
                              'delay_choices_s':[0.] if condition=='C0' else [0.,.02,.04,.06,.10,.14,.18]},
                'replay_trace_sha256':None if args.replay is None else hashlib.sha256(Path(args.replay).read_bytes()).hexdigest(),
                'policy_sha256':hashlib.sha256(policy.read_bytes()).hexdigest(),
                'clock':'virtual seconds shared across all offline roles; single process, no DDS',
                'ROS_target':'Ubuntu24.04/ROS2Jazzy; execution unverified on current Windows host'})
            summaries.append(metrics)
    write_json(out/'summary.json',summaries)
    rows=''.join('<tr>'+''.join(f'<td>{html.escape("N/A" if m[k] is None else str(m[k]))}</td>' for k in ('condition','repeat','received','transport_dropped','discarded_out_of_order','fault_ticks','primary_pass_1s_both_count','primary_missing_both_count','primary_max_both_latency_s'))+'</tr>' for m in summaries)
    (out/'report.html').write_text('<!doctype html><meta charset="utf-8"><title>Week07 transport</title><style>body{font-family:sans-serif;margin:2em}td,th{padding:.6em;border:1px solid #bbb}table{border-collapse:collapse}</style><h1>Week07 synthetic transport experiment</h1><p>Proposed course model. Virtual single-process replay; no ROS/DDS/micro-ROS/physical measurements. N/A/null are missing observations.</p><table><tr><th>Condition</th><th>Repeat</th><th>Received</th><th>Dropped</th><th>Out-of-order</th><th>Fault ticks</th><th>Pass/7</th><th>Missing/7</th><th>Max observed s</th></tr>'+rows+'</table>',encoding='utf-8')
    manifest={str(p.relative_to(out)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
    write_json(out/'manifest.json',{'sha256':manifest,'immutability':'do not edit recorded results; rerun into a new directory'})
    print(f'Wrote {len(summaries)} virtual trials to {out}; physical and ROS latency: N/A')
    return 0

if __name__=='__main__': raise SystemExit(main())
