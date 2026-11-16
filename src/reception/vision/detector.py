"""Face detection with OpenCV's bundled Haar cascade (no model download).

Detection only: no recognition, no identity, frames are never stored.
"""

import cv2
import numpy as np

from reception.config import VisionConfig
from reception.vision.approach import Box


class FaceDetector:
    """Finds frontal faces in a JPEG frame."""

    def __init__(self, cfg: VisionConfig) -> None:
        """Load the cascade that ships with OpenCV."""
        self.cfg = cfg
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"  # type: ignore[attr-defined]
        self.cascade = cv2.CascadeClassifier(path)

    def detect(self, jpeg: bytes) -> list[Box]:
        """Face boxes normalised to the frame; [] for unreadable input.

        Args:
            jpeg: Encoded frame.

        Returns:
            Boxes (fractions of width/height).
        """
        img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return []
        h, w = img.shape[:2]
        img = cv2.equalizeHist(img)
        faces = self.cascade.detectMultiScale(
            img,
            scaleFactor=self.cfg.haar_scale_factor,
            minNeighbors=self.cfg.haar_min_neighbors,
            minSize=(int(h * self.cfg.min_face * 0.6), int(h * self.cfg.min_face * 0.6)),
        )
        return [Box(x / w, y / h, fw / w, fh / h) for (x, y, fw, fh) in faces]
