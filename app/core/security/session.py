import secrets
import time
import uuid


def generate_session_id() -> str:
    """Buat session id unik: uuid hex + epoch miliseconds + 6 karakter alfanumerik.

    Kombinasi ini memberi uniqueness tinggi (uuid) + urutan waktu (timestamp)
    + entropi ekstra (random) — cukup untuk identitas session per login.
    """
    timestamp_ms = int(time.time() * 1000)
    random_suffix = "".join(
        secrets.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
        for _ in range(6)
    )

    return f"{uuid.uuid4().hex}{timestamp_ms}{random_suffix}"
