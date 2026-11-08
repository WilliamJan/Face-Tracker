"""
Image annotation tool: left eye, right eye, nose tip.

Controls (in the image window):
    Left click                    -> left eye  (green)   [eye on the LEFT side of the image]
    Right click                   -> right eye (blue)    [eye on the RIGHT side of the image]
    Middle click OR Shift+Left    -> nose tip  (red)
    Space                         -> save and go to next image (needs all 3 points)
    Backspace                     -> clear points on the current image
    Esc / q                       -> quit (progress is already saved)

Output: annotations.csv with columns
    image_name, left_eye_x, left_eye_y, right_eye_x, right_eye_y, nose_x, nose_y
All coordinates are percentages (0-100) of the image width (x) / height (y).

Requires: pip install opencv-python
Resumes automatically: images already in the CSV are skipped.
"""

import csv
import glob
import os
import re

import cv2

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "dataset", "images")
OUTPUT_CSV = os.path.join(BASE_DIR, "annotations.csv")

WINDOW = "L-click: left eye | R-click: right eye | Middle/Shift+L-click: nose | Space: next | Backspace: reset | Esc: quit"

HEADER = ["image_name", "left_eye_x", "left_eye_y", "right_eye_x", "right_eye_y", "nose_x", "nose_y"]

POINTS = {
    "left_eye": ("L eye", (0, 255, 0)),
    "right_eye": ("R eye", (255, 128, 0)),
    "nose": ("nose", (0, 0, 255)),
}


def natural_key(path):
    """Sort image_2.jpg before image_10.jpg."""
    name = os.path.basename(path)
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", name)]


def load_done(csv_path):
    if not os.path.exists(csv_path):
        return set()
    with open(csv_path, newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        return {row[0] for row in reader if row}


def main():
    paths = []
    for ext in ("jpg", "jpeg", "png"):
        paths += glob.glob(os.path.join(IMAGE_DIR, f"*.{ext}"))
    paths = sorted(set(paths), key=natural_key)

    if not paths:
        print(f"No images found in {IMAGE_DIR}")
        return

    done = load_done(OUTPUT_CSV)
    todo = [p for p in paths if os.path.basename(p) not in done]
    print(f"{len(paths)} images total, {len(done)} already annotated, {len(todo)} to go.")
    if not todo:
        return

    new_file = not os.path.exists(OUTPUT_CSV)
    csv_file = open(OUTPUT_CSV, "a", newline="")
    writer = csv.writer(csv_file)
    if new_file:
        writer.writerow(HEADER)
        csv_file.flush()

    state = {k: None for k in POINTS}

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if flags & cv2.EVENT_FLAG_SHIFTKEY:
                state["nose"] = (x, y)
            else:
                state["left_eye"] = (x, y)
        elif event == cv2.EVENT_RBUTTONDOWN:
            state["right_eye"] = (x, y)
        elif event == cv2.EVENT_MBUTTONDOWN:
            state["nose"] = (x, y)

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(WINDOW, on_mouse)

    i = 0
    quit_all = False
    while i < len(todo) and not quit_all:
        path = todo[i]
        name = os.path.basename(path)
        img = cv2.imread(path)
        if img is None:
            print(f"Could not read {path}, skipping.")
            i += 1
            continue

        h, w = img.shape[:2]
        for k in state:
            state[k] = None

        while True:
            canvas = img.copy()
            r = max(3, min(h, w) // 150)  # marker size scales with image

            for key, (label, color) in POINTS.items():
                p = state[key]
                if p:
                    cv2.circle(canvas, p, r, color, -1)
                    cv2.circle(canvas, p, r + 3, (0, 0, 0), 1)
                    cv2.putText(canvas, label, (p[0] + r + 6, p[1]),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            if state["left_eye"] and state["right_eye"]:
                cv2.line(canvas, state["left_eye"], state["right_eye"], (255, 255, 0), 1)
                if state["nose"]:
                    mid = ((state["left_eye"][0] + state["right_eye"][0]) // 2,
                           (state["left_eye"][1] + state["right_eye"][1]) // 2)
                    cv2.line(canvas, mid, state["nose"], (255, 255, 0), 1)

            status = f"[{i + 1}/{len(todo)}] {name}"
            cv2.putText(canvas, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
            cv2.putText(canvas, status, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.imshow(WINDOW, canvas)
            key = cv2.waitKey(20) & 0xFF

            if key == 32:  # space
                if all(state.values()):
                    row = [name]
                    for k in ("left_eye", "right_eye", "nose"):
                        x, y = state[k]
                        row += [round(x / w * 100, 4), round(y / h * 100, 4)]
                    writer.writerow(row)
                    csv_file.flush()
                    i += 1
                    break
                else:
                    print(f"{name}: need all 3 points (left eye, right eye, nose tip).")
            elif key in (8, 127):  # backspace / delete
                for k in state:
                    state[k] = None
            elif key in (27, ord("q")):  # esc / q
                quit_all = True
                break

            # window closed with the X button
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                quit_all = True
                break

    csv_file.close()
    cv2.destroyAllWindows()
    print(f"Saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()