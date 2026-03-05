"""QR utility helpers."""
import os
import qrcode


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def make_qr_image(url: str, out_path: str, box_size: int = 6):
    qr = qrcode.QRCode(
        version=2,
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=box_size,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(out_path)
