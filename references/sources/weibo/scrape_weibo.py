#!/usr/bin/env python3
# 抓取 @魔法师蛋小丁(2213561393) 全量时间线, 实时筛选「手机推荐」类帖子
# 用法: python3 scrape_weibo.py "<cookie字符串>" [--max-pages 500] [--sleep 1.8]
import sys, json, time, re, os, random, argparse

try:
    import requests
except ImportError:
    sys.exit("需要 requests: pip install requests")

UID = "2213561393"
CONTAINER = f"107603{UID}"
OUT = "/Users/kingsley/.workbuddy/skills/danxiaoding-perspective/references/sources/weibo"
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"

# 手机推荐意图关键词: 命中其一 + 必须含手机语境词 才视为候选
KW = ["推荐","购机","换机","值得买","值不值","性价比","机型","对比","哪款","怎么选",
      "预算","入手","新机","上手机","买哪","选哪","手机怎么","买手机","选手机","换手机",
      "直屏","曲屏","影像旗舰","拍照手机","续航手机","快充手机","千元机","旗舰机","二手机"]
CTX = ["手机","机型","旗舰","影像","直屏","曲屏","千元机","旗舰机"]

def strip_tags(h):
    return re.sub(r"<[^>]+>", "", h or "").strip()

def is_phone_rec(text):
    t = strip_tags(text)
    if not any(k in t for k in CTX):
        return False
    return any(k in t for k in KW)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cookie")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--sleep", type=float, default=1.8)
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    headers = {"User-Agent": UA, "Referer": f"https://m.weibo.cn/u/{UID}",
               "X-Requested-With": "XMLHttpRequest", "Cookie": a.cookie}
    sess = requests.Session(); sess.headers.update(headers)
    hit = 0; scanned = 0; page = 1
    progress = os.path.join(OUT, "progress.json")
    if os.path.exists(progress):
        page = json.load(open(progress)).get("page", 1)
    while page <= a.max_pages:
        url = f"https://m.weibo.cn/api/container/getIndex?containerid={CONTAINER}&page={page}"
        try:
            r = sess.get(url, timeout=20)
            d = r.json()
        except Exception as e:
            print(f"[page {page}] err {e}, retry 5s"); time.sleep(5); continue
        if d.get("ok") not in (1, 200):
            print(f"[page {page}] ok={d.get('ok')} msg={d.get('msg')} -- stop")
            break
        cards = d.get("data", {}).get("cards", [])
        mblogs = [c.get("mblog") for c in cards if isinstance(c, dict) and c.get("mblog")]
        if not mblogs:
            print(f"[page {page}] no mblog, maybe end"); break
        for m in mblogs:
            scanned += 1
            text = m.get("text", "")
            if is_phone_rec(text):
                mid = m.get("id") or m.get("bid")
                item = {"id": mid, "bid": m.get("bid"), "date": m.get("created_at"),
                        "text": strip_tags(text), "raw": text,
                        "url": f"https://weibo.com/{UID}/{m.get('bid')}"}
                with open(os.path.join(OUT, f"{mid}.json"), "w") as f:
                    json.dump(item, f, ensure_ascii=False, indent=2)
                hit += 1
                print(f"[HIT {hit}] {item['date']} {item['text'][:60]}")
        print(f"[page {page}] scanned_total={scanned} hits={hit}")
        json.dump({"page": page + 1, "scanned": scanned, "hits": hit}, open(progress, "w"))
        page += 1
        time.sleep(a.sleep + random.random())
    files = sorted(f for f in os.listdir(OUT) if f.endswith(".json") and f != "progress.json")
    with open(os.path.join(OUT, "index.json"), "w") as f:
        json.dump([json.load(open(os.path.join(OUT, x))) for x in files], f, ensure_ascii=False, indent=2)
    print(f"DONE scanned={scanned} hits={hit} files={len(files)} -> {OUT}")

if __name__ == "__main__":
    main()
