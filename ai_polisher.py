import json
import re
import requests
import config

class AIPolisher:
    """AI 智能润色引擎：将原始英文/抓取内容重构为玩家主理人风格的中文精品专栏"""

    def __init__(self):
        self.session = requests.Session()

    def polish(self, item: dict) -> dict:
        """主入口：尝试 LLM 风格化润色，失败或无 Key 时平滑回退至离线高质量重构"""
        if config.OPENAI_API_KEY:
            try:
                res = self._call_llm(item)
                if res and res.get("title") and res.get("content_md"):
                    return res
            except Exception as e:
                print(f"[AI润色告警] LLM 调用失败，自动切换至离线智能重构: {e}")

        return self._offline_polish(item)

    def _call_llm(self, item: dict) -> dict | None:
        """调用 OpenAI 兼容接口生成结构化 JSON"""
        endpoint = f"{config.OPENAI_API_BASE}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        system_prompt = """你是一名经验丰富、文笔幽默生动的 Steam 游戏专栏特约主理人与资深硬核玩家。
你的任务是将提供的 Steam 游戏官方资讯、版本更新日志或促销活动，深度重构为一篇兼具深度与可读性、排版优雅且极利于搜索引擎 SEO 收录的中文精品文章。

【核心要求与写作规范】：
1. 语言自然：使用中国 PC 玩家熟悉的行话与语气（如“大版本更新”、“平衡性调整”、“背刺”、“史低”、“本体与DLC”、“联机避坑”等）；
2. 结构清晰：采用 Markdown 结构化排版：
   - 🎯 核心看点速览（更新了什么？核心机制变动或折扣信息）
   - 📌 重点深度解析（内容要点、机制改动、角色/数值/地图平衡）
   - 💡 玩家实操与上手建议（开黑技巧、下载安装、配置优化、购买建议）
   - ❓ 常见问题 FAQ（针对该游戏更新或折扣的 2-3 个高频问答）
3. 原文配图语法（如 ![](/static/...) 或 ![](http...)）必须原样保留在合适段落；
4. 【严格违禁词】：严禁在标题、摘要、正文或 FAQ 中提及“采集”、“润色”、“转译”、“机翻”、“翻译”、“大模型”、“AI生成”、“爬虫”等机械词汇！必须以第一人称专业主理人专栏的形式呈现；
5. 输出格式：必须且仅能返回纯 JSON 格式字符串，包含字段：
   - "title": 中文吸引眼球的高点击率标题（25-35字，包含游戏名与核心看点）
   - "summary": 120-160 字的凝练摘要，精准概括要点
   - "categories": ["游戏资讯"] 或 ["特惠折扣"]
   - "tags": 3-5 个中文标签列表（如 ["黑神话悟空", "版本更新", "平衡性调整"]）
   - "content_md": Markdown 格式的完整正文
"""

        appid = item.get("appid", 0)
        game_title = item.get("game_title", "")
        raw_title = item.get("raw_title", "")
        raw_body = item.get("raw_body", "")[:3200]
        item_type = item.get("item_type", "news")

        user_prompt = f"""游戏名称: {game_title} (Steam AppID: {appid})
情报类型: {'特惠折扣' if item_type == 'deal' else '官方更新资讯'}
原标题: {raw_title}
原始内容片段:
{raw_body}"""

        payload = {
            "model": config.OPENAI_MODEL,
            "temperature": config.OPENAI_TEMPERATURE,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        }

        resp = self.session.post(endpoint, json=payload, headers=headers, timeout=45)
        if resp.status_code != 200:
            print(f"[LLM接口报错] HTTP {resp.status_code}: {resp.text}")
            return None

        data = resp.json()
        content_text = data["choices"][0]["message"]["content"].strip()

        # 清除 markdown json 代码块标记
        if content_text.startswith("```"):
            content_text = re.sub(r"^```json\s*", "", content_text)
            content_text = re.sub(r"\s*```$", "", content_text)

        parsed = json.loads(content_text)
        # 确保 tags 和 categories 规范为列表
        if isinstance(parsed.get("tags"), str):
            parsed["tags"] = [t.strip() for t in parsed["tags"].split(",") if t.strip()]
        if isinstance(parsed.get("categories"), str):
            parsed["categories"] = [c.strip() for c in parsed["categories"].split(",") if c.strip()]

        return parsed

    def _offline_polish(self, item: dict) -> dict:
        """离线模式：高质量规则重构引擎（无网络或无 API 时零障碍保底）"""
        appid = item.get("appid", 0)
        game_title = item.get("game_title", f"Steam App {appid}")
        raw_title = item.get("raw_title", "")
        raw_body = item.get("raw_body", "")
        item_type = item.get("item_type", "news")

        # 提取关键亮点语句
        lines = [line.strip() for line in raw_body.split("\n") if line.strip() and not line.startswith("!")]
        highlights = []
        for line in lines[:8]:
            if len(line) > 15 and not line.startswith("http"):
                highlights.append(line)
            if len(highlights) >= 4:
                break

        if item_type == "deal":
            deal = item.get("deal_info", {})
            discount = deal.get("discount_percent", 50)
            orig_p = deal.get("original_price", 0)
            final_p = deal.get("final_price", 0)
            curr = deal.get("currency", "CNY")

            title = f"《{game_title}》限时特惠开启！立省 {discount}% 史低入手指南"
            summary = f"Steam 官方今日推荐特惠：知名佳作《{game_title}》开启大力度折扣，现仅需 {final_p:.2f} {curr}（原价 {orig_p:.2f} {curr}），立省 {discount}%！"
            categories = ["特惠折扣"]
            tags = [game_title, "Steam特惠", "史低折扣", "喜加一"]

            content_md = f"""> 💡 **主理人导读**：PC 玩家喜闻乐见的特惠专栏！Steam 官方今日推送了《{game_title}》的限时高额减免活动，想要补票或喜加一的朋友抓紧关注。

## 🎯 核心看点速览
- **所属游戏**：《{game_title}》（Steam AppID: `{appid}`）；
- **折扣力度**：直降 **-{discount}%**；
- **参考售价**：原价 `{orig_p:.2f} {curr}`，现折后仅需 **`{final_p:.2f} {curr}`**；
- **平台支持**：Steam 官方正版，支持云存档与全套成就。

## 📌 游戏特色与入手分析
《{game_title}》凭借极高的人气与精湛的制作工艺，在 Steam 社区收获了大量玩家好评。本次打折为近期非常值得抄底的入手时机。

## 💡 玩家上手建议与实战技巧
1. **客户端直达**：可通过 `steam://install/{appid}` 或商店页面快速加入购物车；
2. **好友联机推荐**：若游戏支持多人联机，建议拉上好友一起开黑体验更佳。

## ❓ 常见问题 FAQ
**Q1: 购买后是否支持 2 小时无理由退款？**  
A1: 遵循 Steam 官方退款政策，购买 14 天内且游玩时间不超过 2 小时可正常申请退款。

**Q2: 此次特惠是否为历史最低价格？**  
A2: 本次折扣力度高达 -{discount}%，属于入手极佳的史低区间。"""

        else:
            title = f"《{game_title}》重大版本更新与深度解析 (AppID: {appid})"
            summary = f"Steam 官方最新发布《{game_title}》的公告情报。本文深度梳理本次更新关键细节、核心机制优化与实战上手指南。"
            categories = ["游戏资讯"]
            tags = [game_title, "Steam游戏资讯", "版本更新", "更新日志"]

            bullets = "\n".join([f"- {h}" for h in highlights]) if highlights else f"- 针对《{game_title}》进行底层稳定性与性能调优；\n- 修复多项已记录 Bug 并优化联机匹配体验。"

            content_md = f"""> 💡 **主理人导读**：Steam 官方最新发布了《{game_title}》的前沿公告。为了帮助广大玩家第一时间把握最新机制，本期专栏为您带来深度解析。

## 🎯 核心看点速览
- **所属游戏**：《{game_title}》（Steam AppID: `{appid}`）；
- **公告类型**：官方版本更新与性能补丁；
- **重点方向**：平衡性调优、底层稳定性提升与细节体验完善。

## 📌 官方内容重点解析
根据官方发布的公告信息，本次调整重点聚焦于以下关键维度：

{bullets}

## 💡 玩家上手建议与实战技巧
1. **保持版本最新**：建议在 Steam 客户端开启自动更新，确保联机环境版本一致；
2. **客户端极速唤醒**：可通过专属协议 `steam://install/{appid}` 一键唤醒本地客户端进行校验更新。

## ❓ 常见问题 FAQ
**Q1: 更新后进不去游戏或闪退怎么办？**  
A1: 可在 Steam 库中右键游戏 -> 属性 -> 本地文件 -> 验证游戏完整性后重试。

**Q2: 联机网络遇到延迟波动如何优化？**  
A2: 建议检查本地网络节点，或优先选择更近的官方加速服务器进行联机开黑。"""

        return {
            "title": title,
            "summary": summary,
            "categories": categories,
            "tags": tags,
            "content_md": content_md
        }
