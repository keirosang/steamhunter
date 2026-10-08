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
MAX_NEWS_AGE_HOURS = _int(os.getenv("MAX_NEWS_AGE_HOURS"), 48)

_watched_raw = os.getenv("WATCHED_APPIDS", "2358720,1808500,730,1091500,1086940,271590,2344520,1172620,1623730,570,578080,1172470,413150,582010")
WATCHED_APPIDS = [int(x.strip()) for x in _watched_raw.split(",") if x.strip().isdigit()]

# 图床与路径
LOCALIZE_IMAGES = _bool(os.getenv("LOCALIZE_IMAGES"), True)
CONTENT_POSTS_DIR = os.path.join(BASE_DIR, "content", "posts")
STATIC_IMAGES_DIR = os.path.join(BASE_DIR, "static", "images")
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "hugo_crawler.db")

# Hugo 站点配置
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "https://yourname.github.io/").strip()
SITE_TITLE = os.getenv("SITE_TITLE", "Steam 蒸汽猎手 | 独立情报站").strip()
SITE_AUTHOR = os.getenv("SITE_AUTHOR", "SteamHunter").strip()
AUTO_HUGO_BUILD = _bool(os.getenv("AUTO_HUGO_BUILD"), True)

# Git & GitHub 配置
GITHUB_AUTO_PUSH = _bool(os.getenv("GITHUB_AUTO_PUSH"), False)
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL", "").strip()
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip()
GIT_AUTHOR_NAME = os.getenv("GIT_AUTHOR_NAME", "SteamHunter Bot").strip()
GIT_AUTHOR_EMAIL = os.getenv("GIT_AUTHOR_EMAIL", "bot@steamhunter.local").strip()

# 确保核心目录存在
os.makedirs(CONTENT_POSTS_DIR, exist_ok=True)
os.makedirs(STATIC_IMAGES_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
