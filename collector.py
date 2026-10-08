import re
import html
import time
import requests
import config

GAME_NAME_CACHE = {
    2358720: "黑神话：悟空 (Black Myth: Wukong)",
    1808500: "艾尔登法环 (ELDEN RING)",
    730: "反恐精英 2 (Counter-Strike 2)",
    1091500: "赛博朋克 2077 (Cyberpunk 2077)",
    1086940: "博德之门 3 (Baldur's Gate 3)",
    271590: "侠盗猎车手 5 (Grand Theft Auto V)",
    2344520: "暗黑破坏神 4 (Diablo® IV)",
    1172620: "盗贼之海 (Sea of Thieves)",
    1623730: "幻兽帕鲁 (Palworld)",
    570: "刀塔 2 (Dota 2)",
    578080: "绝地求生 (PUBG: BATTLEGROUNDS)",
    1172470: "Apex 英雄 (Apex Legends)",
    413150: "星露谷物语 (Stardew Valley)",
    582010: "怪物猎人：世界 (Monster Hunter: World)"
}

class SteamCollector:
    """Steam 官方新闻与特惠情报采集器"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        })

    def resolve_steam_image_url(self, raw_url: str) -> str:
        """解析并补全 Steam 占位符与 CDN 路径"""
        if not raw_url:
            return ""
        url = str(raw_url).strip().strip("'\"")
        url = url.replace("{STEAM_CLAN_IMAGE}", "https://clan.fastly.steamstatic.com/images")
        url = url.replace("{STEAM_CLAN_LOC_IMAGE}", "https://clan.fastly.steamstatic.com/images")
        url = url.replace("{STEAM_BASE_IMAGE}", "https://clan.fastly.steamstatic.com/images")
        if url.startswith("//"):
            url = f"https:{url}"
        return url

    def clean_bbcode(self, text: str) -> str:
        """清洗 Steam 官方特有的 BBCode 标签"""
        if not text:
            return ""
        text = html.unescape(text)
        text = text.replace("{STEAM_CLAN_IMAGE}", "https://clan.fastly.steamstatic.com/images")
        text = text.replace("{STEAM_CLAN_LOC_IMAGE}", "https://clan.fastly.steamstatic.com/images")
        text = text.replace("{STEAM_BASE_IMAGE}", "https://clan.fastly.steamstatic.com/images")

        # 转换图片与链接
        text = re.sub(r'\[img\](.*?)\[/img\]', r'![](\1)', text, flags=re.IGNORECASE)
        text = re.sub(r'\[url=(.*?)\](.*?)\[/url\]', r'[\2](\1)', text, flags=re.IGNORECASE)
        text = re.sub(r'\[b\](.*?)\[/b\]', r'**\1**', text, flags=re.IGNORECASE)
        text = re.sub(r'\[i\](.*?)\[/i\]', r'*\1*', text, flags=re.IGNORECASE)
        text = re.sub(r'\[h1\](.*?)\[/h1\]', r'## \1\n', text, flags=re.IGNORECASE)
        text = re.sub(r'\[h2\](.*?)\[/h2\]', r'### \1\n', text, flags=re.IGNORECASE)
        text = re.sub(r'\[h3\](.*?)\[/h3\]', r'#### \1\n', text, flags=re.IGNORECASE)
        text = re.sub(r'\[list\]', r'\n', text, flags=re.IGNORECASE)
        text = re.sub(r'\[/list\]', r'\n', text, flags=re.IGNORECASE)
        text = re.sub(r'\[\*\](.*?)', r'- \1', text, flags=re.IGNORECASE)

        # 清除其余多余标签
        text = re.sub(r'\[/?\w+.*?\]', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def get_game_name(self, appid: int) -> str:
        """获取游戏中文/英文名称"""
        if appid in GAME_NAME_CACHE:
            return GAME_NAME_CACHE[appid]
        try:
            url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l=schinese"
            res = self.session.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get(str(appid), {}).get("success"):
                    name = data[str(appid)]["data"].get("name", f"Steam App {appid}")
                    GAME_NAME_CACHE[appid] = name
                    return name
        except Exception:
            pass
        return f"Steam App {appid}"

    def fetch_news_for_app(self, appid: int, count: int = 3) -> list[dict]:
        """抓取指定游戏的最新官方资讯与更新日志"""
        url = f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?appid={appid}&count={count}&maxlength=0&format=json"
        results = []
        try:
            res = self.session.get(url, timeout=12)
            if res.status_code != 200:
                return []
            data = res.json()
            items = data.get("appnews", {}).get("newsitems", [])
            game_title = self.get_game_name(appid)

            now_ts = int(time.time())
            max_age_sec = config.CRAWL_MAX_AGE_DAYS * 86400

            for item in items:
                pub_ts = item.get("date", 0)
                if pub_ts and (now_ts - pub_ts > max_age_sec):
                    continue

                gid = str(item.get("gid", ""))
                if not gid:
                    continue

                raw_body = item.get("contents", "")
                clean_body = self.clean_bbcode(raw_body)

                # 提取第一张配图
                img_match = re.search(r'!\[.*?\]\((https?://[^\s\)]+)\)', clean_body)
                if img_match:
                    img_url = self.resolve_steam_image_url(img_match.group(1))
                else:
                    # 保底使用 Steam 官方封面图
                    img_url = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg"

                results.append({
                    "item_key": f"steam_news_{appid}_{gid}",
                    "item_type": "news",
                    "appid": appid,
                    "gid": gid,
                    "game_title": game_title,
                    "raw_title": item.get("title", f"{game_title} 最新公告"),
                    "raw_body": clean_body,
                    "date_ts": pub_ts,
                    "image_url": img_url,
                    "url": item.get("url", f"https://store.steampowered.com/app/{appid}/")
                })
        except Exception as e:
            print(f"[采集异常] AppID {appid} 抓取失败: {e}")

        return results

    def fetch_steam_specials(self, limit: int = 5) -> list[dict]:
        """抓取 Steam 当前推荐的特惠与大促折扣"""
        url = "https://store.steampowered.com/api/featuredcategories"
        results = []
        try:
            res = self.session.get(url, timeout=12)
            if res.status_code != 200:
                return []
            data = res.json()
            specials = data.get("specials", {}).get("items", [])

            for item in specials[:limit]:
                appid = item.get("id")
                if not appid:
                    continue
                name = item.get("name", "Steam 游戏特惠")
                discount = item.get("discount_percent", 0)
                orig_price = item.get("original_price", 0) / 100.0
                final_price = item.get("final_price", 0) / 100.0
                currency = item.get("currency", "CNY")
                header_image = item.get("header_image", f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg")

                # 生成特惠描述
                today_str = time.strftime("%Y%m%d")
                results.append({
                    "item_key": f"steam_deal_{appid}_{today_str}",
                    "item_type": "deal",
                    "appid": appid,
                    "game_title": name,
                    "raw_title": f"《{name}》限时特惠开启！立省 {discount}% 史低大促",
                    "raw_body": f"Steam 官方推荐特惠活动中，《{name}》当前折扣力度高达 -{discount}%！原价 {orig_price:.2f} {currency}，现仅需 {final_price:.2f} {currency}。活动限时进行中，支持加入库中永久畅玩。",
                    "date_ts": int(time.time()),
                    "image_url": header_image,
                    "deal_info": {
                        "discount_percent": discount,
                        "original_price": orig_price,
                        "final_price": final_price,
                        "currency": currency
                    },
                    "url": f"https://store.steampowered.com/app/{appid}/"
                })
        except Exception as e:
            print(f"[特惠采集异常] 抓取失败: {e}")

        return results

    def collect_all(self, max_items: int = None) -> list[dict]:
        """汇总采集所有符合条件的新鲜情报"""
        limit = max_items or config.MAX_POSTS_PER_RUN
        gathered = []
        print(f"[巡检时效] 设定文章采集跨度: {config.CRAWL_MAX_AGE_DAYS} 天 (最少 1 天，共 {config.MAX_NEWS_AGE_HOURS} 小时)")

        # 1. 采集特惠折扣
        if config.CRAWL_SPECIALS:
            deals = self.fetch_steam_specials(limit=limit)
            gathered.extend(deals)

        # 2. 采集重点游戏资讯
        if config.CRAWL_NEWS:
            for appid in config.WATCHED_APPIDS:
                if len(gathered) >= limit * 2:
                    break
                news_list = self.fetch_news_for_app(appid, count=2)
                gathered.extend(news_list)

        return gathered
