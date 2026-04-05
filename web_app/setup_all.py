import os
import tensorflow as tf
import numpy as np
from PIL import Image

# 1. Folders Create Karein
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")

os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

def create_resources():
    print("⏳ Creating models and folders...")
    
    # EfficientNet Dummy
    m1 = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(224, 224, 3)),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    m1.save(os.path.join(MODEL_DIR, "efficientnet_v2.keras"))

    # ViT Alt Dummy
    m2 = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(224, 224, 3)),
        tf.keras.layers.Flatten(),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    m2.save(os.path.join(MODEL_DIR, "vit_transformer.keras"))

    # Dummy Test Image for predict.py testing
    img = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
    img.save(os.path.join(BASE_DIR, "test.png"))
    
    print("✅ Setup Complete! Folders created and Models saved.")

if __name__ == "__main__":
    create_resources()