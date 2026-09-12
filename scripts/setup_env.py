"""Create local secrets without overwriting an existing environment."""

from pathlib import Path
import secrets, os

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    print("Existing .env preserved.")
else:
    text = (root / ".env.example").read_text()
    text = text.replace(
        "ADMIN_SECRET=\n", "ADMIN_SECRET=" + secrets.token_urlsafe(32) + "\n"
    ).replace(
        "POSTGRES_PASSWORD=\n", "POSTGRES_PASSWORD=" + secrets.token_hex(24) + "\n"
    )
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(text)
    print(
        "Created .env with private local maintenance and database credentials. Read ADMIN_SECRET there to unlock Settings → Maintenance."
    )
