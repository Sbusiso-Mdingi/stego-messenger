import cv2
import numpy as np

def lsb_anomaly_score(image_path: str) -> float:
    """
    Computes a simple statistical score that estimates
    whether an image may contain hidden LSB data.
    Higher score = more suspicious.
    """

    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

    # Get least significant bits
    lsb_plane = img & 1

    # Measure randomness of the LSB plane
    mean = np.mean(lsb_plane)
    std = np.std(lsb_plane)

    score = mean + std
    return float(score)
