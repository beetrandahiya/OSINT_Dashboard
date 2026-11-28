import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import marks
out = pathlib.Path(__file__).resolve().parent.parent / "marks"
for key in marks.MARKS:
    for v in ("full", "small"):
        name = f"{key}.svg" if v == "full" else f"{key}-small.svg"
        (out / name).write_text(marks.svg(key, v) + "\n")
print("ok", len(list(out.glob("*.svg"))))
