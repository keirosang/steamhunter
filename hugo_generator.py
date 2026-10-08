import os
import re
import hashlib
import datetime
from datetime import timezone, timedelta
import yaml
import requests
import config

BJ_TZ = timezone(timedelta(hours=8))

class HugoGenerator:
    """Hugo Markdown 文章生成与配图本地化图床引擎"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        })

    def download_image(self, url: str) -> str:
        """下载远程图片到 static/images/ 目录并返回站内相对路径 /images/{hash}.{ext}"""
        if not url or not config.LOCALIZE_IMAGES:
            return url

        if url.startswith("/images/") or url.startswith("/"):
            return url

        if not url.startswith("http"):
            return url

        try:
            # 去除 query 参数以提取拓展名
            url_clean = url.split("?")[0].strip()
            ext = os.path.splitext(url_clean)[1].lower()
            if not ext or ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
                ext = ".jpg"

            url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
            filename = f"{url_hash[:16]}{ext}"
            filepath = os.path.join(config.STATIC_IMAGES_DIR, filename)

            if not os.path.exists(filepath):
                res = self.session.get(url, timeout=15)
                if res.status_code == 200 and len(res.content) > 500:
                    with open(filepath, "wb") as f:
                        f.write(res.content)
                else:
                    return url

            return f"/images/{filename}"
        except Exception as e:
            print(f"[配图本地化警告] 下载 {url} 失败: {e}")
            return url

    def localize_markdown_images(self, content_md: str) -> str:
        """解析并下载 Markdown 内嵌图片，彻底解决防盗链与 GitHub Pages 破图"""
        if not config.LOCALIZE_IMAGES or not content_md:
            return content_md

        img_pattern = re.compile(r'!\[(.*?)\]\((https?://[^\s\)]+)\)')

        def _replace_img(match):
            alt_text = match.group(1)
            remote_url = match.group(2)
            local_url = self.download_image(remote_url)
            return f"![{alt_text}]({local_url})"

        return img_pattern.sub(_replace_img, content_md)

    def generate_post(self, polished: dict, item: dict) -> str:
        """
        生成 Hugo 规范的 Markdown 文件
        返回生成的文件完整绝对路径
        """
        appid = item.get("appid", 0)
        game_title = item.get("game_title", "")
        item_key = item.get("item_key", "")
        date_ts = item.get("date_ts")

        # 确定发布时间
        if date_ts:
            pub_dt = datetime.datetime.fromtimestamp(int(date_ts), BJ_TZ)
        else:
            pub_dt = datetime.datetime.now(BJ_TZ)

        date_iso = pub_dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        date_prefix = pub_dt.strftime("%Y-%m-%d")

        # 处理封面图本地化
        remote_cover = item.get("image_url", "")
        local_cover = self.download_image(remote_cover)

        # 处理正文图片本地化
        body_md = polished.get("content_md", "")
        body_md = self.localize_markdown_images(body_md)

        # 构造 Front Matter (YAML)
        default_cat = ["限免福利"] if item.get("item_type") == "free" else (["特惠折扣"] if item.get("item_type") == "deal" else ["游戏资讯"])
        categories = polished.get("categories") or default_cat
        if not isinstance(categories, list):
            categories = [categories]

        front_matter = {
            "title": polished.get("title", item.get("raw_title", "Steam 游戏速递")),
            "date": date_iso,
            "lastmod": date_iso,
            "draft": False,
            "author": config.SITE_AUTHOR,
            "categories": categories,
            "tags": polished.get("tags", ["Steam", "游戏资讯"]),
            "summary": polished.get("summary", ""),
            "featured_image": local_cover,
            "appid": appid,
            "game_title": game_title,
            "item_type": item.get("item_type", "news"),
            "type": "posts"
        }

        # 生成 Front Matter YAML 字符串
        fm_yaml = yaml.dump(front_matter, allow_unicode=True, default_flow_style=False, sort_keys=False)

        full_content = f"---\n{fm_yaml}---\n\n{body_md}\n"

        # 生成唯一合法文件名
        safe_key = hashlib.md5(item_key.encode("utf-8")).hexdigest()[:8]
        filename = f"{date_prefix}-{appid}-{safe_key}.md"
        filepath = os.path.join(config.CONTENT_POSTS_DIR, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)

        return filepath
