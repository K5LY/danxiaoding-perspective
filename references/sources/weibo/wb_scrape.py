#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取 @魔法师蛋小丁 (uid 2213561393) 的全部原创微博，
过滤出手机相关帖子，存为 {mid}.json。
用法: python3 wb_scrape.py [max_page]
  max_page 默认为 2000（约覆盖全部 36473 条需要 ~1658 页）
带断点续传：重复运行会从 progress.json 的页码继续。
"""
import urllib.request, json, time, os, re, sys

OUT = "/Users/kingsley/.workbuddy/skills/danxiaoding-perspective/references/sources/weibo"
COOKIE = "SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WharBuQ.8dKdMZ-HUjGnwuw5JpX5KzhUgL.Foz01h-f1heEehz2dJLoIp8zqg4rgJyaU-4aU29aUg4.TBtt;SCF=AssxPPSzWc5fwF51YYfRteQvMI-UfvUa5fnBdEJyGkR2nEhEVW30KVxYDdSMc6LYxhL5g61BKAOoHg9UhLuEqNg.;SUB=_2A25HlraMDeRhGeRN41cU-C3Oyz6IHXVk7bZErDV8PUNbmtAYLWimkW9NU4HUeXRcedgPXDbrxAzlJh1oOtfY3NHb;ALF=02_1790596060;WBPSESS=OqjeA7c6_zt03zhxnh0wT0uts1dA4PmqrwCpin4GB_3Zhv33goL4iP9A2SZNvr_oY9kNme_CInh6fLwX5nH2iE3Yhl5xuC-ZOefKM0aOEakdu478Z6NPQZC3nZT3TY46dPN64egUda5gfSNEd2gOuQ==;XSRF-TOKEN=c1z3RDfJOYD7Q1LH5d47TXen"
UID = "2213561393"
XSRF = "c1z3RDfJOYD7Q1LH5d47TXen"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# 只保留真正锁定"手机硬件/购机"语境的词，避免 AI 工具推荐等误命中
PHONE = ["手机","机型","旗舰","千元机","中端机","直屏","曲屏","曲面屏","折叠屏","影像","拍照",
         "续航","快充","电池","屏幕","处理器","芯片","骁龙","天玑","麒麟","购机","换机","性价比",
         "值得买","入手","预算","新机","测评","评测","上手","二手机","摄像头","镜头","刷新率",
         "OLED","LCD","5G","手机壳","贴膜","充电宝","降频","发热","信号","闪存","内存","RAM",
         "换手机","买手机","选手机","手机怎么","哪款手机","手机推荐","机型推荐","影像旗舰"]

os.makedirs(OUT, exist_ok=True)

def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = s.replace("\u200b", "").replace("\n", " ").replace("\r", " ")
    return re.sub(r"\s+", " ", s).strip()

def match_kw(text):
    t = strip_tags(text)
    hit = [k for k in PHONE if k in t]
    return (hit, "phone") if hit else (None, None)

def fetch(url, retry=4):
    last = None
    for i in range(retry):
        try:
            req = urllib.request.Request(url)
            req.add_header("Cookie", COOKIE)
            req.add_header("User-Agent", UA)
            req.add_header("Referer", "https://weibo.com/u/2213561393")
            req.add_header("Accept", "application/json, text/plain, */*")
            req.add_header("X-XSRF-TOKEN", XSRF)
            resp = urllib.request.urlopen(req, timeout=25)
            return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 403, 502, 503):
                time.sleep(3 * (i + 1))
                continue
            return None
        except Exception as e:
            last = e
            time.sleep(3 * (i + 1))
    return None

def longtext(mid):
    d = fetch(f"https://weibo.com/ajax/statuses/longtext?id={mid}")
    if d and d.get("ok") == 1:
        return d.get("data", {}).get("longTextContent", "")
    return ""

# ---- 断点续传 ----
prog = os.path.join(OUT, "progress.json")
if os.path.exists(prog):
    progress = json.load(open(prog))
else:
    progress = {"page": 0, "done_ids": [], "saved": 0}
done_ids = set(progress.get("done_ids", []))
saved_total = progress.get("saved", 0)

MAX_PAGE = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
empty_streak = 0
consecutive_ids = set()

for page in range(progress["page"] + 1, MAX_PAGE + 1):
    d = fetch(f"https://weibo.com/ajax/statuses/mymblog?uid={UID}&page={page}&feature=0")
    if not d or d.get("ok") != 1:
        empty_streak += 1
        print(f"[warn] page {page} fetch fail ok={d.get('ok') if d else None} streak={empty_streak}", flush=True)
        if empty_streak >= 3:
            print("[stop] 连续 3 次失败，退出", flush=True)
            break
        time.sleep(4)
        continue
    empty_streak = 0
    lst = d.get("data", {}).get("list", [])
    if not lst:
        empty_streak += 1
        if empty_streak >= 3:
            print("[stop] 连续空页，到底", flush=True)
            break
        time.sleep(3)
        continue
    # 重复检测：本页 id 与上一页完全相同 -> 到底/被限
    page_ids = set(str(w.get("id") or w.get("mid")) for w in lst)
    if page_ids and page_ids == consecutive_ids:
        print("[stop] 连续两页 id 完全相同，终止", flush=True)
        break
    consecutive_ids = page_ids

    page_saved = 0
    for w in lst:
        mid = str(w.get("id") or w.get("mid") or w.get("idstr"))
        if not mid or mid in done_ids:
            continue
        done_ids.add(mid)
        # 只保留原创
        if w.get("retweeted_status"):
            continue
        text = w.get("text", "")
        kw, level = match_kw(text)
        if not kw:
            continue
        if w.get("isLongText"):
            lt = longtext(mid)
            if lt:
                text = lt
        item = {
            "mid": mid,
            "created_at": w.get("created_at", ""),
            "keywords": kw,
            "level": level,
            "text": strip_tags(text),
            "text_raw": text,
            "source": w.get("source", ""),
            "reposts": w.get("reposts_count"),
            "comments": w.get("comments_count"),
            "attitudes": w.get("attitudes_count"),
            "is_long": bool(w.get("isLongText")),
            "page_url": f"https://weibo.com/{UID}/{mid}",
        }
        with open(os.path.join(OUT, f"{mid}.json"), "w", encoding="utf-8") as f:
            json.dump(item, f, ensure_ascii=False, indent=2)
        page_saved += 1
        saved_total += 1

    progress["page"] = page
    progress["done_ids"] = list(done_ids)
    progress["saved"] = saved_total
    json.dump(progress, open(prog, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"[ok] page {page:>4} list={len(lst):>2} saved_phone={page_saved:>2} total_saved={saved_total:>4} scanned={len(done_ids):>5}", flush=True)
    time.sleep(1.2)

print(f"[DONE] scanned={len(done_ids)} saved_phone={saved_total}", flush=True)
