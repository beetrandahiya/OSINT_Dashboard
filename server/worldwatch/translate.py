"""Machine translation of headlines into English.

Uses the free endpoint behind Google Translate's web page. It needs no key but it is unofficial: Google can
change or block it at any time. When that happens headlines simply stay in their own language and the
feed's note says so. Every translation is remembered, so a headline is only ever sent once.
Only headline text is sent, nothing about this computer or its owner.
"""
import asyncio
import hashlib
import time

from . import db

URL = "https://translate.googleapis.com/translate_a/single"
BATCH_CHARS = 1500


def _key(lang: str, text: str) -> str:
    return "tr:" + lang + ":" + hashlib.sha1(text.encode()).hexdigest()


async def to_english(fetcher, titles: list[str], lang: str) -> tuple[dict[str, str], int]:
    """Returns ({original: english}, how many could not be translated)."""
    out, todo = {}, []
    for t in dict.fromkeys(titles):
        hit = await asyncio.to_thread(db.lookup_get, _key(lang, t), 90 * 86400)
        if hit:
            out[t] = hit["body"]
        else:
            todo.append(t)
    failed = 0
    while todo:
        batch, size = [], 0
        while todo and (not batch or size + len(todo[0]) < BATCH_CHARS):
            t = todo.pop(0)
            batch.append(t)
            size += len(t) + 1
        try:
            r = await fetcher.client.post(URL, params={"client": "gtx", "sl": lang, "tl": "en", "dt": "t"},
                                          data={"q": "\n".join(x.replace("\n", " ") for x in batch)})
            fetcher.wire_bytes += r.num_bytes_downloaded
            r.raise_for_status()
            lines = "".join(seg[0] for seg in r.json()[0] if seg and seg[0]).split("\n")
            if len(lines) != len(batch):
                raise ValueError("answer does not line up with the question")
            for src, en in zip(batch, lines):
                en = en.strip()
                if en:
                    out[src] = en
                    await asyncio.to_thread(db.lookup_put, _key(lang, src), time.time(), en)
        except Exception:
            failed += len(batch)
        await asyncio.sleep(0.4)
    return out, failed
