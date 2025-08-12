# predict.py
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

# load at import time so a WSGI server with --preload will preload it
_MODEL = load_model()

def predict_from_features(features_list):
    """features_list: 1D list/array matching model input"""
    pred = _MODEL.predict([features_list])
    return float(pred[0])