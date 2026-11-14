# Model weights

Weights are kept out of Git. Download the pretrained starter model explicitly:

```bash
python scripts/download_models.py
```

The YOLO26 profile expects `models/yolo26n.pt`. Point `detector.weights` to a custom fine-tuned `.pt` checkpoint to add project classes. The starter COCO model does not cover every simulation object (for example, the pole, cone and signboard classes require suitable training data).
