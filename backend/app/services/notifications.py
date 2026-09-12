from dataclasses import dataclass


@dataclass(frozen=True)
class Notification:
    title: str
    game_id: int


class NotificationService:
    def __init__(self):
        self.opted_in = False

    def send(self, notification: Notification):
        # Delivery deliberately disabled until a transport and explicit opt-in exist.
        return False
