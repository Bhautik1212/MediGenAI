"""Data-access functions for the `generations` table."""
from datetime import datetime, timezone

from database.db import get_db


def row_to_dict(row):
    d = dict(row)
    d["is_demo"] = bool(d["is_demo"])
    d["image_url"] = f"/api/images/{d['filename']}"
    d["download_url"] = f"/api/history/{d['id']}/download"
    return d


def create_generation(**f):
    db = get_db()
    cur = db.execute(
        """INSERT INTO generations
           (prompt, full_prompt, category, style, aspect_ratio, width, height,
            seed, model_name, provider, is_demo, filename, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            f["prompt"], f["full_prompt"], f["category"], f["style"],
            f["aspect_ratio"], f["width"], f["height"], f.get("seed"),
            f["model_name"], f["provider"], 1 if f["is_demo"] else 0,
            f["filename"], datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
    )
    db.commit()
    return get_generation(cur.lastrowid)


def get_generation(gen_id):
    row = get_db().execute("SELECT * FROM generations WHERE id = ?", (gen_id,)).fetchone()
    return row_to_dict(row) if row else None


def list_generations(page=1, limit=12, category=None):
    db = get_db()
    where, params = "", []
    if category:
        where, params = "WHERE category = ?", [category]
    total = db.execute(f"SELECT COUNT(*) FROM generations {where}", params).fetchone()[0]
    rows = db.execute(
        f"SELECT * FROM generations {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [limit, (page - 1) * limit],
    ).fetchall()
    return [row_to_dict(r) for r in rows], total


def delete_generation(gen_id):
    db = get_db()
    db.execute("DELETE FROM generations WHERE id = ?", (gen_id,))
    db.commit()
