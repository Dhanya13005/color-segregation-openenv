"""
inference.py — AI Color Classification Stub
============================================
This module provides a placeholder for the AI inference pipeline that would
classify the color of an item on the conveyor belt from a camera image or
image patch.

HOW TO SWAP IN A REAL MODEL
-----------------------------
1. Install your model framework:
       pip install torch torchvision   # PyTorch example
       # or: pip install tensorflow    # TensorFlow example
       # or: pip install onnxruntime   # ONNX Runtime example

2. Replace the body of `classify_color()` with:
   a) Load your model (once, at module level or via a lazy singleton).
   b) Pre-process `image_or_patch` (resize, normalize, to tensor).
   c) Run inference.
   d) Map the predicted class index to one of ["red", "blue", "green"].
   e) Return the string.

3. Wire `classify_color()` into your backend route (e.g., a POST /api/classify
   endpoint that accepts a base64-encoded image) and call it from the frontend
   via fetch() instead of the client-side random picker.

Example real-model swap (PyTorch, illustrative):
    import torch
    from torchvision import transforms
    from PIL import Image
    import io, base64

    _model = None   # Lazy-loaded singleton

    def _load_model():
        global _model
        if _model is None:
            _model = torch.load("color_classifier.pt", map_location="cpu")
            _model.eval()
        return _model

    CLASSES = ["red", "blue", "green"]
    _transform = transforms.Compose([
        transforms.Resize((64, 64)),
        transforms.ToTensor(),
        transforms.Normalize([0.5]*3, [0.5]*3),
    ])

    def classify_color(image_or_patch):
        img = Image.open(io.BytesIO(image_or_patch)).convert("RGB")
        tensor = _transform(img).unsqueeze(0)
        with torch.no_grad():
            logits = _load_model()(tensor)
        return CLASSES[logits.argmax(dim=1).item()]
"""

import random
from typing import Union

# ─── Color constants ─────────────────────────────────────────────────────────
VALID_COLORS = ["red", "blue", "green"]

# Optional: average-color thresholds for a simple rule-based approach.
# Useful for testing with solid-color patches from a camera.
_RGB_THRESHOLDS = {
    "red":   lambda r, g, b: r > 150 and g < 100 and b < 100,
    "blue":  lambda r, g, b: b > 150 and r < 100 and g < 100,
    "green": lambda r, g, b: g > 150 and r < 100 and b < 100,
}


def classify_color(image_or_patch: Union[bytes, str, None] = None) -> str:
    """
    Classify the dominant color of a conveyor belt item.

    This is a STUB implementation that demonstrates the expected interface.
    It currently:
      - If `image_or_patch` is a non-empty bytes object, attempts a trivial
        average-pixel heuristic (requires Pillow) and falls back to random.
      - Otherwise, returns a random choice from VALID_COLORS to simulate inference.

    Parameters
    ----------
    image_or_patch : bytes | str | None
        Raw image bytes (JPEG/PNG), a base64-encoded string, or None for
        a fully synthetic demo.

    Returns
    -------
    str
        One of "red", "blue", or "green".

    Raises
    ------
    ValueError
        If the returned color is not in VALID_COLORS (defensive check).
    """

    color = _stub_classify(image_or_patch)

    # Defensive assertion — real model output must also pass this check
    if color not in VALID_COLORS:
        raise ValueError(f"classify_color returned invalid color: {color!r}. Must be one of {VALID_COLORS}.")

    return color


def _stub_classify(image_or_patch) -> str:
    """
    Internal stub logic.
    Swap this function body with real model inference when ready.
    """

    # --- Attempt simple pixel average if Pillow is available ---
    if isinstance(image_or_patch, bytes) and len(image_or_patch) > 0:
        try:
            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_or_patch)).convert("RGB")
            img_small = img.resize((8, 8))  # Sample 8×8 grid for speed
            pixels = list(img_small.getdata())
            avg_r = sum(p[0] for p in pixels) / len(pixels)
            avg_g = sum(p[1] for p in pixels) / len(pixels)
            avg_b = sum(p[2] for p in pixels) / len(pixels)

            for color_name, test_fn in _RGB_THRESHOLDS.items():
                if test_fn(avg_r, avg_g, avg_b):
                    return color_name

            # Fallback: pick highest channel
            max_channel = max(avg_r, avg_g, avg_b)
            if max_channel == avg_r:
                return "red"
            if max_channel == avg_g:
                return "green"
            return "blue"

        except ImportError:
            pass  # Pillow not installed — fall through to random
        except Exception:
            pass  # Corrupt image bytes — fall through to random

    # --- Default: deterministic pseudo-random for demo purposes ---
    # Replace with: return my_real_model.predict(image_or_patch)
    return random.choice(VALID_COLORS)


def batch_classify(images: list) -> list:
    """
    Classify multiple images in one call.
    Useful for batch inference when processing a sequence of frames.

    Parameters
    ----------
    images : list of bytes | str | None
        A list of image_or_patch values (same type as classify_color input).

    Returns
    -------
    list of str
        A list of color strings, one per input image.
    """
    return [classify_color(img) for img in images]


# ─── Self-test / demo ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== inference.py self-test ===")
    print("10 random classifications (no image input):")
    for i in range(10):
        result = classify_color()
        assert result in VALID_COLORS, f"Invalid result: {result}"
        print(f"  [{i+1:02d}] {result}")

    print("\nBatch classification (5 items):")
    results = batch_classify([None] * 5)
    for i, r in enumerate(results):
        print(f"  [{i+1}] {r}")

    print("\nAll tests passed ✓")