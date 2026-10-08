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
        results = []
        game_title = self.get_game_name(appid)
        now_ts = int(time.time())
        max_age_sec = config.CRAWL_MAX_AGE_DAYS * 86400

        try:
            # 优先检索 Steam 官方开发者社区公告与更新日志
            url_official = f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?appid={appid}&count={count}&maxlength=0&format=json&feeds=steam_community_announcements"
            res = self.session.get(url_official, timeout=10)
            items = []
            if res.status_code == 200:
                items = res.json().get("appnews", {}).get("newsitems", [])

            # 若官方公告流为空，退化至全网主流媒体资讯流
            if not items:
                url_fallback = f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v0002/?appid={appid}&count={count}&maxlength=0&format=json"
                res_fb = self.session.get(url_fallback, timeout=10)
                if res_fb.status_code == 200:
                    items = res_fb.json().get("appnews", {}).get("newsitems", [])

            for item in items:
                pub_ts = item.get("date", 0)
                # 严格按配置的时效过滤
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
            pass

        return results

    def _get_app_details(self, appid: int) -> dict:
        """获取 App 详细元数据（中文名、类型、DLC本体归属、价格详情、配图等）"""
        try:
            url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=cn&l=schinese"
            res = self.session.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get(str(appid), {}).get("success"):
                    return data[str(appid)].get("data", {})
        except Exception:
            pass
        return {}

    def fetch_free_giveaways(self, limit: int = 10) -> list[dict]:
        """
        全网限免与喜加一情报深度采集引擎：
        1. Steam 官方商店 100% 减免检索源 (maxprice=free&specials=1)，获取官方在售且当前 100% 折扣的商品与 DLC；
        2. Steam Featured Categories 中 100% 折扣或 0 元促销商品；
        3. 权威游戏福利源 (GamerPower Steam Giveaways)，同步 Steam 官方 Key 码与媒体大促限免；
        自动识别：游戏本体 / DLC 扩展包，提取原价、截止时效、商店链接与一键安装链接。
        """
        results = []
        seen_keys = set()
        today_str = time.strftime("%Y%m%d")

        # 1. Steam 官方商店 100% 减免检索
        try:
            url = "https://store.steampowered.com/search/?maxprice=free&specials=1"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cookie": "birthtime=568022401; lastagecheckage=1-0-1988; wants_mature_content=1"
            }
            res = self.session.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                raw_appids = []
                try:
                    from lxml import etree
                    tree = etree.HTML(res.text)
                    rows = tree.xpath('//a[contains(@class, "search_result_row")]')
                    for r in rows:
                        aid_str = r.attrib.get("data-ds-appid", "")
                        title_text = "".join(r.xpath('.//span[@class="title"]/text()')).strip()
                        pct_text = "".join(r.xpath('.//div[contains(@class, "discount_pct")]/text()')).strip()
                        first_aid = aid_str.split(",")[0].strip() if aid_str else ""
                        if first_aid.isdigit():
                            raw_appids.append((int(first_aid), title_text, pct_text))
                except Exception:
                    matches = re.findall(r'data-ds-appid="(\d+)[^"]*".*?<span class="title">([^<]+)</span>.*?<div class="discount_pct">(-100%)</div>', res.text, re.DOTALL)
                    for m in matches:
                        raw_appids.append((int(m[0]), m[1].strip(), m[2].strip()))

                for aid, fallback_name, pct in raw_appids:
                    item_key = f"steam_free_{aid}"
                    if item_key in seen_keys or aid in seen_keys:
                        continue
                    seen_keys.add(item_key)
                    seen_keys.add(aid)

                    app_info = self._get_app_details(aid)
                    name = app_info.get("name") or fallback_name or f"Steam App {aid}"
                    res_type = app_info.get("type", "game")
                    fullgame = app_info.get("fullgame")
                    fullgame_name = fullgame.get("name") if isinstance(fullgame, dict) else None
                    header_img = app_info.get("header_image") or f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{aid}/header.jpg"
                    short_desc = app_info.get("short_description") or ""

                    price_info = app_info.get("price_overview", {})
                    orig_formatted = price_info.get("initial_formatted", "免费")
                    currency = price_info.get("currency", "CNY")

                    res_type_zh = "🎮 游戏本体" if res_type == "game" else ("🧩 DLC 扩展包" if res_type == "dlc" else "📦 游戏资产")
                    dlc_hint = f"（需拥有《{fullgame_name}》本体方可领取）" if fullgame_name else ""

                    raw_body = (
                        f"Steam 官方商店当前正开启限时喜加一福利活动！\n\n"
                        f"- **福利名称**：《{name}》\n"
                        f"- **资源类型**：{res_type_zh} {dlc_hint}\n"
                        f"- **促销力度**：-100%（原价 {orig_formatted}，现立省 100% 免费领取）\n"
                        f"- **入库规则**：活动期间添加到 Steam 账户，即可永久拥有、终身保留在库！\n\n"
                        f"**内容简介**：\n{short_desc}\n\n"
                        f"**领取方式**：进入 Steam 商店页面点击“添加到账户”或通过客户端一键唤醒安装协议直接入库。"
                    )

                    results.append({
                        "item_key": item_key,
                        "item_type": "free",
                        "free_type": "free_to_keep",
                        "resource_type": res_type,
                        "resource_type_zh": res_type_zh,
                        "fullgame_name": fullgame_name,
                        "appid": aid,
                        "game_title": name,
                        "raw_title": f"🎁【Steam 喜加一】《{name}》限时 100% 减免免费入库！永久保留在库",
                        "raw_body": raw_body,
                        "date_ts": int(time.time()),
                        "image_url": header_img,
                        "deal_info": {
                            "discount_percent": 100,
                            "original_price": price_info.get("initial", 0) / 100.0,
                            "final_price": 0.0,
                            "currency": currency,
                            "is_free": True,
                            "free_type": "free_to_keep",
                            "fullgame_name": fullgame_name,
                            "resource_type_zh": res_type_zh
                        },
                        "url": f"https://store.steampowered.com/app/{aid}/"
                    })
        except Exception as e:
            print(f"[限免采集异常] Steam 100% 检索失败: {e}")

        # 2. 权威游戏福利源 (GamerPower Steam Giveaways)
        if config.CRAWL_GAMERPOWER and len(results) < limit:
            try:
                gp_url = "https://www.gamerpower.com/api/giveaways?platform=steam"
                gp_res = self.session.get(gp_url, timeout=10)
                if gp_res.status_code == 200:
                    gp_data = gp_res.json()
                    now_ts = int(time.time())
                    max_age_sec = config.CRAWL_MAX_AGE_DAYS * 86400

                    for g in gp_data:
                        if len(results) >= limit:
                            break
                        gid = g.get("id")
                        g_title = g.get("title", "")
                        g_url = g.get("open_giveaway_url") or g.get("gamerpower_url")
                        g_worth = g.get("worth", "$0.00")
                        g_instructions = g.get("instructions", "")
                        g_desc = g.get("description", "")
                        g_end = g.get("end_date", "以活动页面截止为准")
                        g_img = g.get("image") or g.get("thumbnail") or ""
                        g_type = g.get("type", "Game")

                        pub_str = g.get("published_date", "")
                        pub_ts = now_ts
                        if pub_str:
                            try:
                                pub_dt = time.strptime(pub_str[:19], "%Y-%m-%d %H:%M:%S")
                                pub_ts = int(time.mktime(pub_dt))
                            except Exception:
                                pass

                        if (now_ts - pub_ts) > max_age_sec:
                            continue

                        item_key = f"steam_gp_giveaway_{gid}"
                        if item_key in seen_keys:
                            continue
                        seen_keys.add(item_key)

                        res_type_zh = "🎮 游戏本体" if "Game" in g_type else ("🧩 DLC 扩展包" if "DLC" in g_type else "🔑 限量激活码")
                        raw_body = (
                            f"Steam 平台正开启限时喜加一福利活动！\n\n"
                            f"- **活动名称**：{g_title}\n"
                            f"- **资源类型**：{res_type_zh}（参考价值：{g_worth}）\n"
                            f"- **截止时间**：{g_end}\n\n"
                            f"**活动内容简介**：\n{g_desc}\n\n"
                            f"**领取步骤指引**：\n{g_instructions}\n\n"
                            f"**官方活动通道**：点击直达活动页面领取 Steam 激活码或一键入库。"
                        )

                        results.append({
                            "item_key": item_key,
                            "item_type": "free",
                            "free_type": "key_giveaway",
                            "resource_type": g_type.lower(),
                            "resource_type_zh": res_type_zh,
                            "appid": 0,
                            "game_title": g_title.replace(" Steam Key Giveaway", "").replace(" Giveaway", ""),
                            "raw_title": f"🎁【Steam 喜加一】{g_title}（价值 {g_worth}，限时免费领取）",
                            "raw_body": raw_body,
                            "date_ts": pub_ts,
                            "image_url": g_img,
                            "deal_info": {
                                "discount_percent": 100,
                                "worth": g_worth,
                                "end_date": g_end,
                                "is_free": True,
                                "free_type": "key_giveaway",
                                "resource_type_zh": res_type_zh
                            },
                            "url": g_url
                        })
            except Exception as e:
                print(f"[限免采集异常] GamerPower 抓取异常: {e}")

        return results[:limit]

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

                results.append({
                    "item_key": f"steam_deal_{appid}_{discount}",
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
        """全类别全网动态情报汇总采集（限免福利最高优先级，资讯与特惠均衡轮候）"""
        limit = max_items or config.MAX_POSTS_PER_RUN
        print(f"[全类别巡检] 启动 Steam 全网全类别动态信息采集模式...")
        print(f"[巡检时效] 设定文章采集跨度: {config.CRAWL_MAX_AGE_DAYS} 天 (最少 1 天，共 {config.MAX_NEWS_AGE_HOURS} 小时)")

        # 1. 顶格优先级：Steam 限免福利与喜加一活动采集
        free_items = []
        if config.CRAWL_FREE:
            free_items = self.fetch_free_giveaways(limit=max(3, limit))
            if free_items:
                print(f"[限免福利雷达] 抓取到正在进行的限免喜加一情报: {len(free_items)} 条")

        # 2. 全类别特惠折扣采集
        deals = []
        if config.CRAWL_SPECIALS:
            deals = self.fetch_steam_specials(limit=max(10, limit * 2))
            if deals:
                print(f"[全网特惠雷达] 抓取到热门大促特惠情报: {len(deals)} 条")

        # 3. 全类别动态游戏资讯巡检（独立配额目标，杜绝被特惠挤压）
        news_items = []
        if config.CRAWL_NEWS:
            game_pool = self.discover_all_category_games(max_games=config.MAX_DISCOVERY_GAMES)
            print(f"[全网动态大盘] 成功汇聚全网热销/新品/特惠/活跃游戏池: {len(game_pool)} 款，正在检索最新官方资讯...")

            target_news_count = max(10, limit * 2)
            for appid, name in game_pool:
                if len(news_items) >= target_news_count:
                    break
                news_list = self.fetch_news_for_app(appid, count=2)
                if news_list:
                    news_items.extend(news_list)

            print(f"[官方资讯雷达] 成功筛选出时效期内游戏官方资讯: {len(news_items)} 条")

        # 4. 科学配比交替组合（保证限免置顶，资讯与特惠交替均衡轮候，彻底杜绝单分类饥饿）
        news_items.sort(key=lambda x: x.get("date_ts", 0), reverse=True)
        deals.sort(key=lambda x: (x.get("deal_info", {}).get("discount_percent", 0), x.get("date_ts", 0)), reverse=True)

        candidates = list(free_items)

        # 交替穿插轮候 (Round-robin: news -> deal -> news -> deal)
        max_len = max(len(news_items), len(deals))
        for i in range(max_len):
            if i < len(news_items):
                candidates.append(news_items[i])
            if i < len(deals):
                candidates.append(deals[i])

        return candidates
