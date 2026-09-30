import os
import cv2
import numpy as np

samples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads', 'samples')
os.makedirs(samples_dir, exist_ok=True)

# 1. Banana Peel (Yellow with brown specks)
img_banana = np.zeros((300, 300, 3), dtype=np.uint8)
img_banana[:] = (245, 245, 245) # light background
# draw crescent curve
cv2.ellipse(img_banana, (150, 160), (100, 45), 35, 0, 180, (40, 205, 240), -1) # yellow (BGR)
cv2.ellipse(img_banana, (150, 160), (95, 38), 35, 0, 180, (50, 220, 255), -1)
# Brown stem tip
cv2.circle(img_banana, (75, 110), 12, (20, 60, 110), -1)
cv2.putText(img_banana, "Banana Peel", (70, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (40, 90, 40), 2)
cv2.imwrite(os.path.join(samples_dir, 'banana_peel.jpg'), img_banana)

# 2. Plastic Bottle (Cyan / Blue translucent bottle)
img_bottle = np.zeros((300, 300, 3), dtype=np.uint8)
img_bottle[:] = (245, 245, 245)
# Bottle neck & cap
cv2.rectangle(img_bottle, (135, 40), (165, 70), (220, 100, 30), -1) # blue cap
cv2.rectangle(img_bottle, (140, 70), (160, 95), (230, 210, 170), -1)
# Bottle body
cv2.rectangle(img_bottle, (110, 95), (190, 230), (240, 215, 180), -1) # PET blue/cyan
cv2.rectangle(img_bottle, (110, 95), (190, 230), (200, 140, 50), 2)
cv2.putText(img_bottle, "PET Plastic Bottle", (40, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 80, 20), 2)
cv2.imwrite(os.path.join(samples_dir, 'plastic_bottle.jpg'), img_bottle)

# 3. Lithium Battery (Silver cylinder, red positive terminal, danger symbol)
img_battery = np.zeros((300, 300, 3), dtype=np.uint8)
img_battery[:] = (30, 30, 35) # dark background
# Battery casing
cv2.rectangle(img_battery, (90, 70), (210, 225), (160, 160, 165), -1)
cv2.rectangle(img_battery, (130, 50), (170, 70), (40, 40, 220), -1) # red positive terminal
cv2.rectangle(img_battery, (100, 90), (200, 200), (30, 30, 35), -1)
cv2.putText(img_battery, "Li-ion", (115, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 210, 240), 2)
cv2.putText(img_battery, "3.7V", (125, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
cv2.putText(img_battery, "Lithium Battery", (55, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 100, 255), 2)
cv2.imwrite(os.path.join(samples_dir, 'battery.jpg'), img_battery)

# 4. Circuit Board (Green solder mask with copper lines and black chip)
img_pcb = np.zeros((300, 300, 3), dtype=np.uint8)
img_pcb[:] = (40, 110, 30) # PCB Green
# Traces
for y in range(50, 250, 25):
    cv2.line(img_pcb, (30, y), (270, y), (50, 190, 230), 2) # copper trace
# IC chip
cv2.rectangle(img_pcb, (110, 100), (190, 180), (25, 25, 25), -1)
for p in range(115, 185, 12):
    cv2.line(img_pcb, (p, 90), (p, 100), (200, 200, 200), 2)
    cv2.line(img_pcb, (p, 180), (p, 190), (200, 200, 200), 2)
cv2.putText(img_pcb, "MCU", (128, 148), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
cv2.putText(img_pcb, "PCB Circuit Board", (45, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
cv2.imwrite(os.path.join(samples_dir, 'circuit_board.jpg'), img_pcb)

# 5. Newspaper (Dry recyclable)
img_news = np.zeros((300, 300, 3), dtype=np.uint8)
img_news[:] = (235, 235, 235)
cv2.rectangle(img_news, (60, 40), (240, 230), (250, 250, 250), -1)
cv2.rectangle(img_news, (60, 40), (240, 230), (180, 180, 180), 2)
cv2.putText(img_news, "DAILY NEWS", (75, 75), cv2.FONT_HERSHEY_DUPLEX, 0.65, (40, 40, 40), 2)
for ly in range(95, 215, 15):
    cv2.line(img_news, (75, ly), (225, ly), (140, 140, 140), 1)
cv2.putText(img_news, "Recyclable Newspaper", (30, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 60, 60), 2)
cv2.imwrite(os.path.join(samples_dir, 'newspaper.jpg'), img_news)

print("Sample images generated successfully!")
