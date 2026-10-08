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
    """Steam 全类别官方新闻与特惠情报动态采集器"""

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
            res = self.session.get(url, timeout=8)
            if res.status_code == 200:
                data = res.json()
                if data.get(str(appid), {}).get("success"):
                    name = data[str(appid)]["data"].get("name", f"Steam App {appid}")
                    GAME_NAME_CACHE[appid] = name
                    return name
        except Exception:
            pass
        return f"Steam App {appid}"

    def discover_all_category_games(self, max_games: int = None) -> list[tuple[int, str]]:
        """
        全类别全网游戏动态发现引擎：
        从 Steam 全网官方数据源动态抓取：
        1. Steam Featured Categories (全网特惠 specials、全网热销 top_sellers、全网新品 new_releases、期待新游 coming_soon)
        2. Steam ISteamChartsService (全网最热门在线活跃 Top 100 游戏排行榜)
        3. 自定义追加的 AppID (可选)
        彻底打破固定 AppID 限制，实现全网全类别游戏大盘覆盖。
        """
        limit_pool = max_games or config.MAX_DISCOVERY_GAMES
        discovered = []
        seen_ids = set()

        # 0. 优先加入自定义 AppID（若有配置）
        for aid in config.CUSTOM_APPIDS:
            if aid not in seen_ids:
                seen_ids.add(aid)
                discovered.append((aid, self.get_game_name(aid)))

        # 1. 动态抓取 Steam 官方精选全类别大盘 (特惠/热销/新品/期待)
        try:
            url = "https://store.steampowered.com/api/featuredcategories"
            res = self.session.get(url, timeout=12)
            if res.status_code == 200:
                data = res.json()
                for cat in ["top_sellers", "new_releases", "specials", "coming_soon"]:
                    for item in data.get(cat, {}).get("items", []):
                        aid = item.get("id")
                        name = item.get("name", "")
                        if aid and aid not in seen_ids:
                            seen_ids.add(aid)
                            discovered.append((aid, name))
                            if name:
                                GAME_NAME_CACHE[aid] = name
        except Exception as e:
            print(f"[全网大盘动态发现异常] featuredcategories: {e}")

        # 2. 动态抓取 Steam 当前实时最热门在线活跃 Top 100 游戏
        try:
            charts_url = "https://api.steampowered.com/ISteamChartsService/GetMostPlayedGames/v1/"
            res = self.session.get(charts_url, timeout=12)
            if res.status_code == 200:
                ranks = res.json().get("response", {}).get("ranks", [])
                for rank_item in ranks:
                    aid = rank_item.get("appid")
                    if aid and aid not in seen_ids:
                        seen_ids.add(aid)
                        discovered.append((aid, self.get_game_name(aid)))
                    if len(discovered) >= limit_pool:
                        break
        except Exception as e:
            print(f"[热门榜单动态发现异常] GetMostPlayedGames: {e}")

        return discovered[:limit_pool]

    def fetch_news_for_app(self, appid: int, count: int = 3) -> list[dict]:
        """抓取指定游戏的最新官方资讯与更新日志（严格限制在 CRAWL_MAX_AGE_DAYS 时效内）"""
        url = f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?appid={appid}&count={count}&maxlength=0&format=json"
        results = []
        try:
            res = self.session.get(url, timeout=10)
            if res.status_code != 200:
                return []
            data = res.json()
            items = data.get("appnews", {}).get("newsitems", [])
            game_title = self.get_game_name(appid)

            now_ts = int(time.time())
            max_age_sec = config.CRAWL_MAX_AGE_DAYS * 86400

            for item in items:
                pub_ts = item.get("date", 0)
                # 严格按配置的时效（最少 1 天 / 24 小时）过滤
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
            # 忽略极少数单游接口网络波动
            pass

        return results

    def fetch_steam_specials(self, limit: int = 10) -> list[dict]:
        """抓取 Steam 全网全品类实时推荐特惠与大促折扣"""
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
            print(f"[全类别特惠采集异常] 抓取失败: {e}")

        return results

    def collect_all(self, max_items: int = None) -> list[dict]:
        """全类别全网动态情报汇总采集"""
        limit = max_items or config.MAX_POSTS_PER_RUN
        gathered = []
        print(f"[全类别巡检] 启动 Steam 全网全类别动态信息采集模式...")
        print(f"[巡检时效] 设定文章采集跨度: {config.CRAWL_MAX_AGE_DAYS} 天 (最少 1 天，共 {config.MAX_NEWS_AGE_HOURS} 小时)")

        # 1. 全类别特惠折扣采集
        if config.CRAWL_SPECIALS:
            deals = self.fetch_steam_specials(limit=limit * 2)
            gathered.extend(deals)

        # 2. 全类别动态游戏情报巡检（打破固定 AppID 限制）
        if config.CRAWL_NEWS:
            game_pool = self.discover_all_category_games(max_games=config.MAX_DISCOVERY_GAMES)
            print(f"[全网动态大盘] 成功汇聚全网热销/新品/特惠/活跃游戏池: {len(game_pool)} 款")

            # 遍历动态大盘游戏，获取时效范围内的官方公告
            for appid, name in game_pool:
                if len(gathered) >= limit * 3:
                    break
                news_list = self.fetch_news_for_app(appid, count=2)
                gathered.extend(news_list)

        # 按情报发布时间倒序排列，优先处理最新鲜的情报
        gathered.sort(key=lambda x: x.get("date_ts", 0), reverse=True)
        return gathered
