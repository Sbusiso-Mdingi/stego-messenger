import cv2
import numpy as np


# ----------------------------
# JPEG Compression Attack
# ----------------------------
def jpeg_compress(image_path, quality=30):
    img = cv2.imread(image_path)
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    _, encimg = cv2.imencode(".jpg", img, encode_param)
    decimg = cv2.imdecode(encimg, 1)
    return decimg


# ----------------------------
# Gaussian Noise Attack
# ----------------------------
def add_gaussian_noise(image, mean=0, std=10):
    noise = np.random.normal(mean, std, image.shape).astype("uint8")
    noisy_img = cv2.add(image, noise)
    return noisy_img


# ----------------------------
# Cropping Attack
# ----------------------------
def crop_image(image, crop_ratio=0.9):
    h, w, _ = image.shape
    new_h = int(h * crop_ratio)
    new_w = int(w * crop_ratio)
    return image[:new_h, :new_w]


# ----------------------------
# Resize Attack
# ----------------------------
def resize_image(image, scale=0.5):
    h, w, _ = image.shape
    return cv2.resize(image, (int(w * scale), int(h * scale)))
