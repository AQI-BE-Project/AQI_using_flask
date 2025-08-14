import os
import pickle

MODEL_PATH = os.environ.get("MODEL_PATH", "new_model_realtime.pickle")
_model = None

def load_model():
    global _model
    if _model is None:
        with open(MODEL_PATH, "rb") as f:
            _model = pickle.load(f)
    return _model

_MODEL = load_model()

def predict_from_features(features_list):
    pred = _MODEL.predict([features_list])
    return float(pred[0])
