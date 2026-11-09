import os
import hashlib

MODEL_PATH = "models/teachable_model/keras_model.h5"
LABELS_PATH = "models/teachable_model/labels.txt"

def klassifiziere_bild(pil_bild):
    labels = ["H&M", "Zara", "Patagonia", "Armedangels", "Secondhand/Vintage"]
    
    if os.path.exists(MODEL_PATH) and os.path.exists(LABELS_PATH):
        try:
            import tensorflow as tf
            import numpy as np
            model = tf.keras.models.load_model(MODEL_PATH, compile=False)
            img = pil_bild.convert("RGB").resize((224, 224))
            arr = (np.array(img, dtype=np.float32) / 127.5) - 1.0
            data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
            data[0] = arr
            pred = model.predict(data)
            idx = np.argmax(pred[0])
            return {"label": labels[idx], "konfidenz": round(float(pred[0][idx]), 2), "modus": "Teachable Machine (.h5)"}
        except Exception as e:
            pass

    # Dummy Simulation falls noch kein Modell hochgeladen ist
    hash_val = int(hashlib.md5(pil_bild.tobytes()).hexdigest(), 16)
    idx = hash_val % len(labels)
    return {"label": labels[idx], "konfidenz": 0.88, "modus": "Teachable Machine Simulation (Dummy)"}
