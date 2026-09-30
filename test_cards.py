import sys
sys.path.insert(0, 'src')

from PySide6.QtWidgets import QApplication
from aircontrol.gui.main_window import MainWindow, InfoCard
from PySide6.QtGui import QColor

app = QApplication(sys.argv)

# Test 1: Check if InfoCard frame renders with correct background
card = InfoCard("Test", "VALUE")
print(f"Card styleSheet: [{card.styleSheet()}]")
print(f"Card autoFillBackground: {card.autoFillBackground()}")
print(f"Card palette bg color: {card.palette().color(card.backgroundRole()).name()}")

# Test 2: Check label stylesheets
print(f"\nTitle text: '{card._title_label.text()}'")
print(f"Title style: '{card._title_label.styleSheet()}'")
print(f"Title autoFillBackground: {card._title_label.autoFillBackground()}")
print(f"Title palette bg: {card._title_label.palette().color(card._title_label.backgroundRole()).name()}")

print(f"\nValue text: '{card._value_label.text()}'")
print(f"Value style: '{card._value_label.styleSheet()}'")
print(f"Value autoFillBackground: {card._value_label.autoFillBackground()}")

# Test 3: Test with setAutoFillBackground on frame
card2 = InfoCard("Test2", "VALUE2")
card2.setAutoFillBackground(True)
print(f"\n--- After setAutoFillBackground(True) ---")
print(f"Card2 palette bg: {card2.palette().color(card2.backgroundRole()).name()}")
print(f"Card2 styleSheet: [{card2.styleSheet()}]")

# Test 4: Verify all 10 cards have text
win = MainWindow()
cards = [
    win._status_card, win._fps_card, win._detected_card,
    win._handedness_card, win._confidence_card, win._gesture_card,
    win._voice_status_card, win._voice_phrase_card, win._voice_action_card,
    win._cursor_card,
]
print("\n=== All Cards ===")
for c in cards:
    print(f"  '{c._title_label.text()}: {c._value_label.text()}'")
    assert c._title_label.text(), f"Empty title!"
    assert c._value_label.text(), f"Empty value!"

print("\nALL CARDS HAVE TEXT - issue is purely rendering")
app.deleteLater()
