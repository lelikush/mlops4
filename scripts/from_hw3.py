"""Стадия 0 для студента: выход split из ДЗ 3 -> data/train.jsonl, data/val.jsonl.

Почему не простое копирование. Split в ДЗ 3 групповой (group_key = topic),
но на моём наборе он выродился: train 2992, val 0, test 0. Причины две:
  1. в group_split цель каждого сплита сравнивалась с НАКОПЛЕННЫМ числом
     назначенных строк — после train val-цель (299) уже «достигнута»;
  2. тема `other` — 74% набора, а при seed 42 она последняя в порядке
     перемешивания, так что train забирает все группы даже с правильной целью.

Здесь — детерминированный групповой сплит без перемешивания: группы
по убыванию размера, каждая целиком уходит в первый сплит, чья НАКОПЛЕННАЯ
цель ещё не набрана. Тема по-прежнему не пересекает границу сплитов.
"""

import json
from collections import defaultdict
from pathlib import Path

from src.config import load_params


def main() -> None:
    params = load_params()
    cfg = params["hw3"]
    src_dir = Path(cfg["split_dir"])
    if not src_dir.exists():
        raise SystemExit(f"Нет {src_dir} — укажите hw3.split_dir в params.yaml")

    records: list[dict] = []
    for name in ("train", "val", "test"):
        path = src_dir / f"{name}.jsonl"
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                records += [json.loads(line) for line in fh if line.strip()]

    groups: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        groups[r["topic"].strip().lower()].append(r)
    order = sorted(groups, key=lambda k: (-len(groups[k]), k))

    ratios = cfg["ratios"]
    names = list(ratios)
    bounds, acc = [], 0.0
    for name in names:
        acc += ratios[name]
        bounds.append(round(acc * len(records)))

    buckets: dict[str, list[dict]] = {n: [] for n in names}
    assigned, cur = 0, 0
    for key in order:
        while cur < len(names) - 1 and assigned >= bounds[cur]:
            cur += 1
        buckets[names[cur]] += groups[key]
        assigned += len(groups[key])

    out = {"train": params["data"]["train_jsonl"], "val": params["data"]["val_jsonl"]}
    for name, rows in buckets.items():
        path = Path(out.get(name, str(Path(out["train"]).with_name(f"{name}.jsonl"))))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        topics = sorted({r["topic"] for r in rows})
        print(f"  {name}: {len(rows)} примеров ({len(rows) / len(records):.1%}), темы: {', '.join(topics)}")


if __name__ == "__main__":
    main()
