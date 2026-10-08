import os
from dotenv import load_dotenv

# 确保以 hugo-page 目录为基准定位配置文件
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

def _bool(val: str, default: bool = False) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in ("true", "1", "yes", "on")

def _int(val: str, default: int = 0) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def _float(val: str, default: float = 0.0) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

# LLM 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_TEMPERATURE = _float(os.getenv("OPENAI_TEMPERATURE"), 0.7)

# 采集与巡检配置
CRAWL_NEWS = _bool(os.getenv("CRAWL_NEWS"), True)
CRAWL_SPECIALS = _bool(os.getenv("CRAWL_SPECIALS"), True)
MAX_POSTS_PER_RUN = _int(os.getenv("MAX_POSTS_PER_RUN"), 5)

# 采集时间跨度（天数，最少为 1 天；若配置小于 1 则强制按 1 天处理）
_days_env = os.getenv("CRAWL_MAX_AGE_DAYS") or os.getenv("MAX_NEWS_AGE_DAYS")
if _days_env is not None and str(_days_env).strip() != "":
    CRAWL_MAX_AGE_DAYS = max(1, _int(_days_env, 1))
else:
    _hours_env = os.getenv("MAX_NEWS_AGE_HOURS")
    if _hours_env is not None and str(_hours_env).strip() != "":
        CRAWL_MAX_AGE_DAYS = max(1, _int(_hours_env, 24) // 24)
    else:
        CRAWL_MAX_AGE_DAYS = 1

MAX_NEWS_AGE_HOURS = CRAWL_MAX_AGE_DAYS * 24

# 全网全类别动态发现机制（默认开启，自动汇聚 Steam 全网特惠、热销榜、新品榜与在线活跃大作）
ENABLE_DYNAMIC_DISCOVERY = _bool(os.getenv("ENABLE_DYNAMIC_DISCOVERY"), True)
MAX_DISCOVERY_GAMES = _int(os.getenv("MAX_DISCOVERY_GAMES"), 120)

# 可选自定义追加 AppID（选填，若填写则优先加入全网巡检池，但不以此为限）
_custom_raw = os.getenv("CUSTOM_APPIDS", "")
CUSTOM_APPIDS = [int(x.strip()) for x in _custom_raw.split(",") if x.strip().isdigit()]

# 图床与路径
LOCALIZE_IMAGES = _bool(os.getenv("LOCALIZE_IMAGES"), True)
CONTENT_POSTS_DIR = os.path.join(BASE_DIR, "content", "posts")
STATIC_IMAGES_DIR = os.path.join(BASE_DIR, "static", "images")
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "hugo_crawler.db")

# Hugo 站点配置
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://keirosang.github.io/steamhunter/").strip()
SITE_TITLE = os.getenv("SITE_TITLE", "Steam 蒸汽猎手 | 游戏情报站").strip()
SITE_AUTHOR = os.getenv("SITE_AUTHOR", "SteamHunter").strip()
AUTO_HUGO_BUILD = _bool(os.getenv("AUTO_HUGO_BUILD"), True)

# Git & GitHub Pages 直接部署配置（无需 GitHub Actions）
GITHUB_AUTO_PUSH = _bool(os.getenv("GITHUB_AUTO_PUSH"), False)
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL", "").strip()
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip()
GITHUB_PAGES_BRANCH = os.getenv("GITHUB_PAGES_BRANCH", "gh-pages").strip()
GIT_AUTHOR_NAME = os.getenv("GIT_AUTHOR_NAME", "SteamHunter Bot").strip()
GIT_AUTHOR_EMAIL = os.getenv("GIT_AUTHOR_EMAIL", "bot@steamhunter.local").strip()

# 确保核心目录存在
os.makedirs(CONTENT_POSTS_DIR, exist_ok=True)
os.makedirs(STATIC_IMAGES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
