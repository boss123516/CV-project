"""Scenario selection and launch preparation; no ROS import during inspection."""
import argparse
from importlib.util import find_spec
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from cv_project.config import ROOT,read_json,pipeline_config,scenario_config,resolve_path,runtime_dir


def process_alive(pid):
    try:
        os.kill(pid,0)
        return Path(f'/proc/{pid}/stat').read_text().split(') ',1)[1][0]!='Z'
    except (OSError,ValueError):return False


def doctor(config):
    checks={name:find_spec(name) is not None for name in ['numpy','cv2','PIL','rclpy']}
    webots=os.environ.get('WEBOTS_BIN') or shutil.which('webots')
    if not webots:
        home=os.environ.get('WEBOTS_HOME')
        webots=str(Path(home)/'webots') if home else str(Path.home()/'.ros/webotsR2025a/webots/webots')
    checks['webots']=Path(webots).is_file() and os.access(webots,os.X_OK)
    if config['detector']['backend']=='yolo26':
        checks['ultralytics']=find_spec('ultralytics') is not None
        checks['model_weights']=resolve_path(config['detector']['weights']).is_file()
    return checks


def main(argv=None):
    parser=argparse.ArgumentParser(prog='cv-project')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('list-scenarios');sub.add_parser('status');sub.add_parser('stop')
    sub.add_parser('list-pipelines')
    for name in ['start','doctor','world']:
        child=sub.add_parser(name)
        child.add_argument('--scenario',default=os.environ.get('CV_SCENARIO','urban_baseline'))
        child.add_argument('--pipeline',default='baseline',help='baseline, yolo26, or a JSON path')
        if name=='start':
            child.add_argument('--no-viewer',action='store_true');child.add_argument('--no-voice',action='store_true')
            child.add_argument('--mode',choices=['realtime','fast'],default='realtime')
            child.add_argument('--dry-run',action='store_true')
    args=parser.parse_args(argv)
    if args.command=='list-scenarios':
        for path in sorted((ROOT/'scenarios').glob('*/scenario.json')):
            data=read_json(path);print(f"{data['id']:24} {data['title_ko']}")
        return 0
    if args.command=='list-pipelines':
        for path in sorted((ROOT/'config/pipelines').glob('*.json')):
            data=read_json(path);print(f"{data['name']:12} {data['description']}")
        return 0
    if args.command=='stop':
        return subprocess.call(['bash',str(ROOT/'webots/scripts/stop_demo.sh')])
    if args.command=='status':
        entries={path.stem:{'pid':int(path.read_text()),'running':process_alive(int(path.read_text()))}
                 for path in runtime_dir().glob('*.pid')}
        metadata=runtime_dir()/'run.json'
        print(json.dumps({'run':read_json(metadata) if metadata.exists() else None,'components':entries},ensure_ascii=False,indent=2))
        return 0
    path=resolve_path(f'config/pipelines/{args.pipeline}.json' if args.pipeline in ['baseline','yolo26'] else args.pipeline)
    config=pipeline_config(path);scene=scenario_config(args.scenario)
    if args.command=='world':
        print(resolve_path(scene['manifest']['world']));return 0
    if args.command=='doctor':
        checks=doctor(config);print(json.dumps(checks,indent=2));return 0 if all(checks.values()) else 1
    components=['sim','detector','perception']
    if config['components'].get('viewer',True) and not args.no_viewer:components.append('viewer')
    if config['components'].get('voice',True) and not args.no_voice:components.append('voice')
    plan={'pipeline':config['name'],'config':str(path),'scenario':args.scenario,
          'world':scene['manifest']['world'],'components':components,'mode':args.mode}
    if args.dry_run:print(json.dumps(plan,ensure_ascii=False,indent=2));return 0
    checks=doctor(config)
    if not all(checks.values()):
        print('Missing runtime requirements: '+', '.join(key for key,value in checks.items() if not value),file=sys.stderr)
        print('See docs/SETUP.md and scripts/download_models.py.',file=sys.stderr);return 1
    metadata=runtime_dir()/'run.json'
    alive=any(process_alive(int(p.read_text())) for p in runtime_dir().glob('*.pid'))
    if alive and metadata.exists() and read_json(metadata)!=plan:
        parser.error('A different pipeline/scenario is running. Stop it before switching.')
    if alive and not metadata.exists():
        parser.error('A legacy demo is running. Stop it before starting a configured pipeline.')
    env=dict(os.environ,CV_PROJECT_ROOT=str(ROOT),CV_PROJECT_CONFIG=str(path),CV_SCENARIO=args.scenario,
             CV_COMPONENTS=' '.join(components),CV_WEBOTS_MODE=args.mode,CV_RUN_DIR=str(runtime_dir()))
    result=subprocess.call(['bash',str(ROOT/'webots/scripts/start_demo.sh')],env=env)
    if result==0:
        metadata.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
        time.sleep(2)
        failed=[name for name in components if not (runtime_dir()/f'{name}.pid').exists() or not process_alive(int((runtime_dir()/f'{name}.pid').read_text()))]
        if failed:
            print('Components exited during startup: '+', '.join(failed)+'. Inspect '+str(runtime_dir()),file=sys.stderr)
            return 1
    return result
