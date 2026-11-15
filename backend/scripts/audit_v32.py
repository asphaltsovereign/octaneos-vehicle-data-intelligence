"""Print partition and calibration audit for a trained Sentinel V3.2 artifact."""
from pathlib import Path
import argparse, json, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.model_store import load_bundle


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--model-dir',default='artifacts/sentinel_baseline_v32'); args=ap.parse_args()
    _, m=load_bundle(args.model_dir)
    train=set(m.get('train_vehicle_ids',[])); cal=set(m.get('calibration_vehicle_ids',[])); test=set(m.get('test_vehicle_ids',[]))
    print('SENTINEL V3.3 MODEL AUDIT')
    print('model_version:',m.get('model_version'))
    print('vehicles train/cal/test:',len(train),len(cal),len(test))
    print('overlap train-cal:',len(train & cal)); print('overlap train-test:',len(train & test)); print('overlap cal-test:',len(cal & test))
    print('windows train/cal/test:',m.get('training_windows'),m.get('calibration_windows'),m.get('test_windows'))
    print('features:',m.get('feature_count')); print('capabilities:',m.get('capability_signals'))
    print('weights:',m.get('ensemble_weights')); print('threshold:',m.get('decision_threshold'))
    c=m.get('calibration',{})
    print('cal target normal FPR:',c.get('target_normal_fpr'))
    print('cal achieved normal FPR:',c.get('calibration_normal_fpr'))
    print('cal injected positive recall:',c.get('calibration_injected_positive_recall'))
    print('artifact sha256:',m.get('artifact_sha256'))

if __name__=='__main__': main()
