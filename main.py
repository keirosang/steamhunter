#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Steam 蒸汽猎手 - 独立采集与 GitHub Pages 自动发布系统
======================================================
功能特性：
1. 独立运行、独立 .env 配置，无任何外部代码依赖；
2. 自动巡检 Steam 官方资讯公告、特惠大促与限免情报；
3. 本地化流式下载配图，杜绝 GitHub Pages 防盗链破图；
4. LLM 智能玩家主理人风格润色（支持 OpenAI/DeepSeek/Gemini/中转等，无 Key 时内置高保真离线重构引擎）；
5. 自动生成标准规范的 Hugo Markdown 文章并调用本地 Hugo 构建；
6. 自动 Git 暂存、提交，并一键推送到 GitHub Pages 仓库进行线上发布。
"""

import sys
import os
import argparse

import config
from storage import HugoStorage
from collector import SteamCollector
from ai_polisher import AIPolisher
from hugo_generator import HugoGenerator
from git_syncer import GitSyncer

def print_banner():
    banner = r"""
  ╔═══════════════════════════════════════════════════════════════╗
  ║    🎮 Steam 蒸汽猎手 · Hugo + GitHub Pages 独立采集发布系统     ║
  ║    独立环境 | AI 玩家主理人润色 | 本地防盗链图床 | 自动推送发布    ║
  ╚═══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def run_pipeline(limit: int = None, dry_run: bool = False, skip_crawl: bool = False, skip_build: bool = False, skip_push: bool = False):
    storage = HugoStorage()
    collector = SteamCollector()
    polisher = AIPolisher()
    generator = HugoGenerator()
    syncer = GitSyncer()

    effective_limit = limit or config.MAX_POSTS_PER_RUN
    new_generated_files = []

    print(f"[配置检查] 单次配额: {effective_limit} 篇 | 模型: {config.OPENAI_MODEL} | 自动推送: {config.GITHUB_AUTO_PUSH}")
    print(f"[数据底表] 本地历史已入库文章总量: {storage.get_total_crawled()} 篇\n")

    # 1. 采集阶段
    if not skip_crawl:
        print(">>> 步骤 1/4: 开始全网巡检 Steam 情报源...")
        candidates = collector.collect_all(max_items=effective_limit * 2)
        print(f"[巡检完成] 发现候选情报条目: {len(candidates)} 条")

        processed_count = 0
        for item in candidates:
            if processed_count >= effective_limit:
                break

            item_key = item.get("item_key")
            title = item.get("raw_title")
            appid = item.get("appid")
            game_title = item.get("game_title")

            # 去重检查 1: 精确唯一键检查（已抓取的 news gid / deal / free key）
            if storage.is_crawled(item_key):
                continue

            # 去重检查 2: 促销周期冷却（同一款游戏的特惠或限免在 N 天内不重复发文）
            item_type = item.get("item_type")
            if item_type in ("deal", "free") and appid:
                cooldown_days = config.DEAL_COOLDOWN_DAYS if item_type == "deal" else config.FREE_COOLDOWN_DAYS
                if storage.has_recent_article(appid, item_type=item_type, days=cooldown_days):
                    continue

            print(f"\n[新情报捕获] 《{game_title}》 (AppID: {appid}) - {title}")

            if dry_run:
                print("  [DRY-RUN 试运行] 跳过 AI 润色与文件写入。")
                processed_count += 1
                continue

            # 2. AI 润色阶段
            print("  🤖 正在调用 AI 进行主理人风格重构与排版...")
            polished = polisher.polish(item)
            polished_title = polished.get("title", title)
            print(f"  ✨ 润色完成: 《{polished_title}》")

            # 3. 生成 Hugo Markdown 与本地化图床
            print("  📝 正在生成 Hugo Markdown 并本地化缓存配图...")
            md_path = generator.generate_post(polished, item)
            rel_path = os.path.relpath(md_path, config.BASE_DIR)
            print(f"  ✅ 成功写入: {rel_path}")

            # 记录到 SQLite 本地底表防重复
            storage.mark_crawled(item_key, item.get("item_type"), appid, polished_title, rel_path)
            new_generated_files.append(rel_path)
            processed_count += 1

        print(f"\n[采集统计] 本轮成功发布新增文章: {len(new_generated_files)} 篇")
    else:
        print(">>> 跳过采集与 Markdown 生成步骤。")

    # 4. 本地 Hugo 静态构建
    if not skip_build and config.AUTO_HUGO_BUILD:
        print("\n>>> 步骤 2/4: 执行本地 Hugo 静态网页构建...")
        syncer.build_hugo()

    # 5. Git 同步与推送到 GitHub
    if not skip_push:
        print("\n>>> 步骤 3/4: 执行 Git 提交与 GitHub 同步...")
        commit_msg = f"Auto publish: {len(new_generated_files)} new articles from collector [skip ci]" if new_generated_files else "Auto sync hugo site updates [skip ci]"
        syncer.sync_to_github(commit_msg)

    print("\n>>> 步骤 4/4: 全部流程处理完毕！🎉")

def show_status():
    storage = HugoStorage()
    total = storage.get_total_crawled()
    recent = storage.get_recent_crawled(limit=8)
    print(f"\n📊 【站点运营状态汇总】")
    print(f"  - 数据库文件: {config.DB_PATH}")
    print(f"  - 已入库文章总计: {total} 篇")
    print(f"  - 最近收录记录:")
    if not recent:
        print("    (暂无记录)")
    for r in recent:
        print(f"    • [{r.get('item_type')}] {r.get('title')} -> {r.get('hugo_file')} ({r.get('created_at')})")
    print("")

def main():
    parser = argparse.ArgumentParser(description="Steam 蒸汽猎手 - 独立 Hugo 采集与 GitHub Pages 自动发布系统")
    parser.add_argument("--crawl", action="store_true", help="仅执行数据采集与 Markdown 生成")
    parser.add_argument("--build", action="store_true", help="仅执行 Hugo 本地构建")
    parser.add_argument("--push", action="store_true", help="仅执行 Git 提交与 GitHub 远程推送")
    parser.add_argument("--status", action="store_true", help="查看当前数据库收录与运行状态")
    parser.add_argument("--limit", type=int, default=None, help="指定本轮抓取生成的最大文章数量")
    parser.add_argument("--dry-run", action="store_true", help="测试运行（仅抓取显示，不保存文件及入库）")

    args = parser.parse_args()

    print_banner()

    if args.status:
        show_status()
        return

    if args.crawl:
        run_pipeline(limit=args.limit, dry_run=args.dry_run, skip_crawl=False, skip_build=True, skip_push=True)
    elif args.build:
        run_pipeline(limit=args.limit, dry_run=args.dry_run, skip_crawl=True, skip_build=False, skip_push=True)
    elif args.push:
        run_pipeline(limit=args.limit, dry_run=args.dry_run, skip_crawl=True, skip_build=True, skip_push=False)
    else:
        # 默认完整闭环运行
        run_pipeline(limit=args.limit, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
