#!/usr/bin/env python3
"""Explicitly download the YOLO26 starter checkpoint; do not start training."""
import argparse
import shutil
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--model',choices=['yolo26n.pt','yolo26s.pt','yolo26m.pt'],default='yolo26n.pt')
parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'models')
args=parser.parse_args()
from ultralytics import YOLO
args.output.mkdir(parents=True,exist_ok=True)
model=YOLO(args.model)
source=Path(model.ckpt_path).resolve();target=(args.output/args.model).resolve()
if source!=target:shutil.copy2(source,target)
print(target)
