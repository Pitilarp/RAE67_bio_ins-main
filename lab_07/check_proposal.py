"""Check proposal completeness. Does not certify correctness or ethics approval."""
import argparse
import json
import math
from pathlib import Path

def text_complete(value):
    return isinstance(value,str) and bool(value.strip()) and not value.strip().upper().startswith(('TODO','TBD'))

def parameter_value_complete(value):
    if isinstance(value,bool):
        return False
    if isinstance(value,(int,float)):
        try:
            return math.isfinite(value)
        except OverflowError:
            return False
    if isinstance(value,str):
        return text_complete(value)
    if isinstance(value,list):
        return bool(value) and all(parameter_value_complete(x) for x in value)
    return False

def validate(plan):
    if not isinstance(plan,dict):
        return ['proposal must be a JSON object']
    failures=[]
    for key in ('question','hypothesis','biological_inspiration_source','independent_variable','AHM_equation','SO2_CPG_equation','integration_description'):
        if not text_complete(plan.get(key)): failures.append(key+' requires a concrete explanation/source')
    conditions=plan.get('conditions',[])
    if not isinstance(conditions,list):
        failures.append('conditions must be a list of objects')
        conditions=[]
    if len(conditions)<2 or not any(isinstance(x,dict) and x.get('baseline') is True for x in conditions): failures.append('at least2conditions including a declared baseline')
    names=[x.get('name') for x in conditions if isinstance(x,dict)]
    complete_names=[n.strip().casefold() for n in names if text_complete(n)]
    if len(complete_names)!=len(conditions) or len(set(complete_names))!=len(complete_names): failures.append('condition names unique and complete')
    for c in conditions:
        if not isinstance(c,dict):
            failures.append('every condition must be an object')
            continue
        if not text_complete(c.get('change')) or type(c.get('repeats')) is not int or c['repeats']<3: failures.append('eachcondition needs change and>=3repeats')
    metrics=plan.get('metrics',[])
    if not isinstance(metrics,list):
        failures.append('metrics must be a list of objects')
        metrics=[]
    names=[m.get('name') for m in metrics if isinstance(m,dict)]
    complete_names=[n.strip().casefold() for n in names if text_complete(n)]
    if len(set(complete_names))<2: failures.append('at least2 distinct metrics with complete names')
    if len(set(complete_names))!=len(complete_names): failures.append('metric names must be unique')
    for metric in metrics:
        if not isinstance(metric,dict):
            failures.append('every metric must be an object')
            continue
        if not all(text_complete(metric.get(k)) for k in ('name','unit','measurement','missing_rule')): failures.append('everymetric needs name/unit/measurement/missingrule')
    if not isinstance(plan.get('controls'),list) or len(plan['controls'])<3 or not all(text_complete(x) for x in plan['controls']): failures.append('atleast3concretecontrols')
    for key in ('simulation_plan','real_robot_plan','clock_correlation_plan','safety_stop_plan','order_counterbalancing','paired_seed_or_participant_plan','expected_input_ids_before_run','timeline'):
        if not text_complete(plan.get(key)): failures.append(key+' must be specified')
    if type(plan.get('human_scenario_duration_s')) is not int or plan['human_scenario_duration_s']<600: failures.append('human scenario must be>=600s;22s replay doesnotreplaceit')
    parameters=plan.get('parameters',[])
    if not isinstance(parameters,list):
        failures.append('parameters must be a list of objects')
        parameters=[]
    for p in parameters:
        if not isinstance(p,dict):
            failures.append('every parameter must be an object')
            continue
        if not all(text_complete(p.get(k)) for k in ('name','unit','provenance')) or not parameter_value_complete(p.get('value')): failures.append('parameter name/value/unit/provenance incomplete; numeric values must be finite')
    if not parameters: failures.append('parameter/equationtable required')
    return failures

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('proposal',nargs='?',default='proposal.json'); args=parser.parse_args()
    try:
        plan=json.loads(Path(args.proposal).read_text(encoding='utf-8'))
    except (OSError,ValueError) as error:
        print('FAIL: cannot read proposal JSON: '+str(error))
        return 1
    failures=validate(plan)
    print('PASS: fields complete; lecturer must review scientific validity' if not failures else 'FAIL: proposal fields incomplete or invalid')
    for f in failures: print(' - '+f)
    return bool(failures)

if __name__=='__main__': raise SystemExit(main())
