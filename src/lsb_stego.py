from PIL import Image
import numpy as np

DELIMITER = "#####END#####"  

def bytes_to_binary(data: bytes) -> str:
    return ''.join(format(byte, '08b') for byte in data)

def binary_to_bytes(binary: str) -> bytes:
    return bytes(int(binary[i:i+8], 2) for i in range(0, len(binary), 8))

def embed_data(image_path: str, data: bytes, output_path: str):
    img = Image.open(image_path)
    arr = np.array(img)

    binary_message = bytes_to_binary(data + DELIMITER.encode())
    flat = arr.flatten()

    if len(binary_message) > len(flat):
        raise ValueError("Payload too large for this image")

    for i, bit in enumerate(binary_message):
        flat[i] = (flat[i] & 0b11111110) | int(bit)

    stego = flat.reshape(arr.shape)
    Image.fromarray(stego).save(output_path)

def extract_data(image_path: str) -> bytes:
    img = Image.open(image_path)
    arr = np.array(img)
    flat = arr.flatten()

    bits = [str(p & 1) for p in flat]
    bit_string = ''.join(bits)

    raw_bytes = binary_to_bytes(bit_string)

    delimiter = DELIMITER.encode()
    end = raw_bytes.find(delimiter)

    if end == -1:
        raise ValueError("No hidden data found")

    return raw_bytes[:end]
