#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二次抓取：在已抓到的 922 条(核心手机术语)基础上，用更宽的关键词
(品牌/机型/元器件) 重新翻 @魔法师蛋小丁 2023 起的全部微博，补齐语料到 1000+。
按「已存文件」去重，只新增未保存的帖，不覆盖/不删除旧文件。
用法: python3 wb_scrape_broad.py [max_page]
"""
import urllib.request, json, time, os, re, sys

OUT = "/Users/kingsley/.workbuddy/skills/danxiaoding-perspective/references/sources/weibo"
COOKIE = open("/tmp/wb_cookie.txt").read().strip()
UID = "2213561393"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# 核心手机术语（命中即 core，与第一次口径一致）
CORE = ["手机","机型","旗舰","千元机","中端机","直屏","曲屏","曲面屏","折叠屏","影像","拍照",
        "续航","快充","电池","屏幕","处理器","芯片","骁龙","天玑","麒麟","购机","换机","性价比",
        "值得买","入手","预算","新机","测评","评测","上手","二手机","摄像头","镜头","刷新率",
        "OLED","LCD","5G","手机壳","贴膜","充电宝","降频","发热","信号","闪存","内存","RAM",
        "换手机","买手机","选手机","手机怎么","哪款手机","手机推荐","机型推荐","影像旗舰"]
# 无歧义元器件/影像技术（手机专属，命中即 brand 级，无需共现）
COMP_STRICT = ["AMOLED","LTPO","BOE","京东方","维信诺","豪威","IMX","徕卡","蔡司","哈苏",
               "UFS","LPDDR","屏下指纹","无线充电","反向充电","卫星通信","卫星","eSIM","灵动岛"]
# 需与手机语境共现的元器件（已剔除显卡/显示器歧义词）
COMP_CTX = ["CMOS","传感器","高刷","调光","长焦","超广角","主摄","副摄","广角","挖孔"]
# 纯手机品牌：几乎只做手机，命中即算手机帖（高精度）
PURE_PHONE = ["一加","realme","真我","魅族","红魔","坚果","努比亚"]
# 综合品牌：也做车/笔记本/AI，需配手机语境或具体机型才算
CONGLOM = ["小米","红米","华为","荣耀","苹果","iPhone","OPPO","vivo","三星","Samsung","索尼",
           "Sony","谷歌","Pixel","华硕","ROG","中兴","联想","摩托罗拉","台积电","联发科","高通","海思"]
# 手机语境词（综合品牌/泛元器件与之共现才算手机帖）
PHONE_CTX = ["手机","机型","屏","摄","镜","芯片","续航","充电","发布","新机","旗舰","影像","体验",
             "评测","上手","购机","换机","性价比","预算","入手","直屏","曲屏","折叠","快充","电池",
             "信号","拍照","高刷","刷新率","调光","重量","厚度","屏幕","摄像头","处理器"]
# 纯生活闲聊拒绝词库（数码科技语料不需要）：命中即排除
DENY = ["果汁","苹果汁","美食","餐厅","旅游","景点","基金","股票","房产","医院","天气","快递",
        "感冒","疫苗","电影","演唱会","相亲","减肥","健身卡","外卖"]
# 具体机型正则：品牌后必须跟「 distinguishable 系列词」或「数字」
# 单字母系列(P/X/S/K/Z)必须跟数字，避免误匹配 PC/套件 等
MODEL_RE = re.compile(
    r"(小米|红米|Redmi|华为|荣耀|iPhone|OPPO|vivo|一加|realme|真我|三星|魅族|Pixel|ROG|红魔|努比亚|摩托罗拉|联想)"
    r"\s*((Mate|Civi|MIX|Find|Reno|Magic|Note|GT|Edge|Neo|Pro|Ultra|Max|Plus|Air|Flip|Fold)\s*\d{0,3}"
    r"|(X|S|K|Z|P)\s*\d{1,3}"
    r"|\d{1,3}[A-Za-z]*)")

os.makedirs(OUT, exist_ok=True)

def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = s.replace("\u200b", "").replace("\n", " ").replace("\r", " ")
    return re.sub(r"\s+", " ", s).strip()

def match_kw(text):
    t = strip_tags(text)
    if any(c in t for c in DENY):
        return None, None                      # 纯生活闲聊排除
    hit_c = [k for k in CORE if k in t]
    if hit_c:
        return hit_c, "phone"                  # 与首轮口径一致（已有 922）
    # —— 数码科技口径的增量信号 ——
    hit_s = [k for k in COMP_STRICT if k in t]
    if hit_s:
        return hit_s, "comp"                   # 无歧义元器件/影像技术
    if any(b in t for b in PURE_PHONE):
        return ["pure_phone"], "pure_phone"    # 纯手机品牌
    if MODEL_RE.search(t):
        return ["model"], "model"              # 具体机型名
    if any(b in t for b in CONGLOM):
        return ["brand"], "brand"              # 综合品牌裸词（数码科技口径）
    return None, None

def fetch(url, retry=4):
    for i in range(retry):
        try:
            req = urllib.request.Request(url)
            req.add_header("Cookie", COOKIE)
            req.add_header("User-Agent", UA)
            req.add_header("Referer", "https://weibo.com/u/2213561393")
            req.add_header("Accept", "application/json, text/plain, */*")
            resp = urllib.request.urlopen(req, timeout=25)
            return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 403, 502, 503):
                time.sleep(3 * (i + 1)); continue
            return None
        except Exception:
            time.sleep(3 * (i + 1))
    return None

def longtext(mid):
    d = fetch(f"https://weibo.com/ajax/statuses/longtext?id={mid}")
    if d and d.get("ok") == 1:
        return d.get("data", {}).get("longTextContent", "")
    return ""

# 已存文件（去重基准）
existing = set()
for f in os.listdir(OUT):
    if f.endswith(".json") and f not in ("progress.json","index.json","progress_broad.json"):
        existing.add(f[:-5])
print(f"[init] 已存在手机帖文件: {len(existing)}", flush=True)

# 断点（仅按页码续传；mid 去重靠 existing）
prog = os.path.join(OUT, "progress_broad.json")
if os.path.exists(prog):
    progress = json.load(open(prog))
else:
    progress = {"page": 0}
start = progress["page"]
saved_total = progress.get("saved_new", 0)
scanned_pages = progress.get("scanned_pages", 0)

MAX_PAGE = int(sys.argv[1]) if len(sys.argv) > 1 else 700
empty_streak = 0
consecutive_ids = set()
new_saved = 0

for page in range(start + 1, MAX_PAGE + 1):
    d = fetch(f"https://weibo.com/ajax/statuses/mymblog?uid={UID}&page={page}&feature=0")
    if not d or d.get("ok") != 1:
        empty_streak += 1
        print(f"[warn] page {page} fetch fail ok={d.get('ok') if d else None} streak={empty_streak}", flush=True)
        if empty_streak >= 3:
            print("[stop] 连续 3 次失败，退出", flush=True); break
        time.sleep(4); continue
    empty_streak = 0
    lst = d.get("data", {}).get("list", [])
    if not lst:
        empty_streak += 1
        if empty_streak >= 3:
            print("[stop] 连续空页，到底", flush=True); break
        time.sleep(3); continue
    page_ids = set(str(w.get("id") or w.get("mid")) for w in lst)
    if page_ids and page_ids == consecutive_ids:
        print("[stop] 连续两页 id 完全相同，终止", flush=True); break
    consecutive_ids = page_ids

    page_saved = 0
    for w in lst:
        mid = str(w.get("id") or w.get("mid") or w.get("idstr"))
        if not mid or mid in existing:
            continue
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
        existing.add(mid)
        page_saved += 1
        new_saved += 1

    scanned_pages += 1
    progress["page"] = page
    progress["saved_new"] = new_saved
    progress["scanned_pages"] = scanned_pages
    json.dump(progress, open(prog, "w"), ensure_ascii=False)
    print(f"[ok] page {page:>4} list={len(lst):>2} new_phone={page_saved:>2} new_total={new_saved:>4} (累计文件={len(existing)})", flush=True)
    time.sleep(1.2)

print(f"[DONE] 新增手机帖={new_saved} 累计文件={len(existing)}", flush=True)
