# rubox/keyboard.py

class Button:
    def __init__(self, button_text: str, id: str, type: str = "Simple"):
        self.button_text = button_text
        self.id = id
        self.type = type

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "button_text": self.button_text
        }

class KeypadRow:
    def __init__(self, buttons: list[Button]):
        self.buttons = buttons

    def to_dict(self):
        return {
            "buttons": [button.to_dict() for button in self.buttons]
        }

class Keypad:
    def __init__(self, rows: list[KeypadRow], resize_keyboard: bool = False, on_time_keyboard: bool = False):
        self.rows = rows
        self.resize_keyboard = resize_keyboard
        self.on_time_keyboard = on_time_keyboard

    def to_dict(self):
        return {
            "rows": [row.to_dict() for row in self.rows],
            "resize_keyboard": self.resize_keyboard,
            "on_time_keyboard": self.on_time_keyboard
        }
