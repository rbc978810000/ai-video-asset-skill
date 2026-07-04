from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ai_video_asset_skill.main_orchestrator import create_market_mining_project_dir
from ai_video_asset_skill.file_manager import create_project_dirs
from ai_video_asset_skill.market_mining import (
    _dedupe_works,
    _filter_topic_relevant_buyer_prompts,
    _select_detail_rows,
    analyze_market_keywords,
    build_vjshi_search_url,
    fetch_vjshi_work_detail,
    fetch_vjshi_work_details_batch,
    mine_market,
    parse_vjshi_search_results,
    parse_vjshi_work_detail,
)
from ai_video_asset_skill.market_reference_assets import _score_reference_candidate
from ai_video_asset_skill.vjshi_search import build_vjshi_keyword_search_url, fetch_vjshi_search_results


SEARCH_HTML = """
<html>
  <body>
    <a href="/watch/123456.html" title="端午节龙舟竞渡航拍视频素材">
      <img src="https://pic.vjshi.com/2025/cover/dragon.jpg" alt="端午节龙舟竞渡航拍视频素材" />
      <span>286购买</span><span>4K</span><span>00:18</span><span>AIGC</span>
    </a>
    <a href="https://www.vjshi.com/watch/222333.html" title="粽子蒸汽特写端午美食">
      <img src="https://pic.vjshi.com/2025/cover/zongzi.webp" />
      <span>89下载</span><span>1080P</span><span>12秒</span>
    </a>
  </body>
</html>
"""

DETAIL_HTML = """
<html>
  <head>
    <title>端午节龙舟竞渡航拍视频素材-光厂</title>
    <meta name="keywords" content="端午节,龙舟,赛龙舟,航拍,水花,节日宣传片" />
  </head>
  <body>
    <h1>端午节龙舟竞渡航拍视频素材</h1>
    <p>素材收入 ￥530 上传时间 2025-05-18 作者 航拍工厂 分类 节日民俗</p>
    <img src="https://pic.vjshi.com/2025/detail/dragon_01.jpg" />
    <video src="https://cdn.vjshi.com/preview/123456.mp4"></video>
    <a href="/watch/999888.html">相关作品</a>
  </body>
</html>
"""


class MarketMiningTests(unittest.TestCase):
    def test_parse_search_results_extracts_sales_and_cover(self) -> None:
        rows = parse_vjshi_search_results(SEARCH_HTML, "端午 龙舟", "https://www.vjshi.com/search?wd=x")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["work_id"], "123456")
        self.assertEqual(rows[0]["purchase_count"], 286)
        self.assertEqual(rows[0]["resolution"], "4K")
        self.assertTrue(rows[0]["aigc_flag"])
        self.assertIn("dragon.jpg", rows[0]["cover_url"])
        self.assertEqual(rows[1]["download_count"], 89)

    def test_parse_work_detail_extracts_keywords_income_and_preview(self) -> None:
        detail = parse_vjshi_work_detail(
            DETAIL_HTML,
            {"work_id": "123456", "work_url": "https://www.vjshi.com/watch/123456.html"},
        )
        self.assertIn("龙舟", detail["detail_keywords"])
        self.assertEqual(detail["material_income"], 530)
        self.assertEqual(detail["upload_time"], "2025-05-18")
        self.assertIn("dragon_01.jpg", detail["preview_images"][0])
        self.assertIn("123456.mp4", detail["preview_video_url"])

    def test_parse_work_detail_extracts_income_before_label_with_wan_unit(self) -> None:
        detail = parse_vjshi_work_detail(
            """
            <html>
              <body>
                <h1>商务握手签约视频素材</h1>
                <section>
                  <div>2.8万元</div><div>1年前</div><div>视频素材</div>
                  <div>3840*2160</div><div>25p</div><div>2025年</div>
                  <div>素材收入</div><div>上传时间</div><div>素材类型</div>
                  <div>分辨率</div><div>帧率</div><div>创作时间</div>
                </section>
              </body>
            </html>
            """,
            {"work_id": "222333", "work_url": "https://www.vjshi.com/watch/222333.html"},
        )
        self.assertEqual(detail["material_income"], 28000)

    def test_parse_work_detail_ignores_author_30_day_income(self) -> None:
        detail = parse_vjshi_work_detail(
            """
            <html>
              <body>
                <h1>商务握手签约视频素材</h1>
                <aside>作者近30天收入 9.9万元</aside>
                <section>2.8万元 1年前 视频素材 3840*2160 25p 2025年 素材收入 上传时间 素材类型 分辨率 帧率 创作时间</section>
              </body>
            </html>
            """,
            {"work_id": "222333", "work_url": "https://www.vjshi.com/watch/222333.html"},
        )
        self.assertEqual(detail["material_income"], 28000)

    def test_parse_work_detail_does_not_use_author_income_without_material_label(self) -> None:
        detail = parse_vjshi_work_detail(
            """
            <html>
              <body>
                <h1>商务握手签约视频素材</h1>
                <aside>作者近30天收入 9.9万元</aside>
              </body>
            </html>
            """,
            {"work_id": "222333", "work_url": "https://www.vjshi.com/watch/222333.html"},
        )
        self.assertIsNone(detail["material_income"])

    def test_parse_work_detail_does_not_use_author_income_as_material_income(self) -> None:
        detail = parse_vjshi_work_detail(
            """
            <html>
              <body>
                <h1>商务握手签约视频素材</h1>
                <aside>作者近30天收入 9.9万元</aside>
                <section>素材收入 上传时间 素材类型 分辨率 帧率 创作时间</section>
              </body>
            </html>
            """,
            {"work_id": "222333", "work_url": "https://www.vjshi.com/watch/222333.html"},
        )
        self.assertIsNone(detail["material_income"])

    def test_parse_work_detail_does_not_read_upload_age_as_income(self) -> None:
        detail = parse_vjshi_work_detail(
            """
            <html>
              <body>
                <h1>新材料科研团队实验室研发团队大学科研人员</h1>
                <section>素材收入 上传时间 素材类型 分辨率 帧率 创作时间 1年前 视频素材 3840*2160 25p 2025年</section>
              </body>
            </html>
            """,
            {"work_id": "35522250", "work_url": "https://www.vjshi.com/watch/35522250.html"},
        )
        self.assertIsNone(detail["material_income"])

    def test_parse_work_detail_extracts_income_after_label_with_money_unit(self) -> None:
        detail = parse_vjshi_work_detail(
            """
            <html>
              <body>
                <h1>新材料科研团队实验室研发团队大学科研人员</h1>
                <section>素材收入 2.8万元 上传时间 1年前 视频素材 3840*2160 25p 2025年</section>
              </body>
            </html>
            """,
            {"work_id": "35522250", "work_url": "https://www.vjshi.com/watch/35522250.html"},
        )
        self.assertEqual(detail["material_income"], 28000)

    def test_parse_work_detail_does_not_read_seo_download_keyword_as_download_count(self) -> None:
        detail = parse_vjshi_work_detail(
            """
            <html>
              <body>
                <h1>大学科研人员绘制图纸 国产大飞机 视频素材包下载</h1>
                <section>
                  素材详情 素材标题 大学科研人员绘制图纸 国产大飞机 素材编号 35014680
                  文件大小 3.2G 上传日期 2025-02-11 点击 219次 购买 9次
                  光厂(VJshi)视频提供大学科研人员绘制图纸 国产大飞机 视频素材 下载，适用于 C919设计师。
                </section>
              </body>
            </html>
            """,
            {"work_id": "35014680", "work_url": "https://www.vjshi.com/watch/35014680.html"},
        )
        self.assertEqual(detail["purchase_count"], 9)
        self.assertEqual(detail["click_count"], 219)
        self.assertIsNone(detail["download_count"])

    def test_parse_work_detail_extracts_explicit_download_count(self) -> None:
        detail = parse_vjshi_work_detail(
            """
            <html>
              <body>
                <h1>测试素材</h1>
                <section>素材详情 素材标题 测试素材 上传日期 2025-02-11 点击 219次 购买 9次 下载 89次</section>
              </body>
            </html>
            """,
            {"work_id": "download-1", "work_url": "https://www.vjshi.com/watch/35014680.html"},
        )
        self.assertEqual(detail["download_count"], 89)

    def test_parse_work_detail_reads_download_times_from_serialized_data(self) -> None:
        detail = parse_vjshi_work_detail(
            """
            <html>
              <body>
                <script>window.__data = [\"downloadTimes\",762,\"entityType\",\"NP\"];</script>
                <section>素材详情 素材标题 测试素材 上传日期 2019-10-27 点击 9,218次 购买 762次 下载后无模糊，高清实拍素材</section>
              </body>
            </html>
            """,
            {"work_id": "download-2", "work_url": "https://www.vjshi.com/watch/4015538.html"},
        )
        self.assertEqual(detail["download_count"], 762)

    def test_parse_work_detail_does_not_read_post_purchase_copy_as_download_count(self) -> None:
        detail = parse_vjshi_work_detail(
            """
            <html>
              <body>
                <section>素材详情 素材标题 测试素材 上传日期 2019-10-27 点击 9,218次 购买 762次 下载后无模糊，高清实拍素材</section>
              </body>
            </html>
            """,
            {"work_id": "download-3", "work_url": "https://www.vjshi.com/watch/4015538.html"},
        )
        self.assertIsNone(detail["download_count"])

    def test_parse_work_detail_falls_back_to_purchase_when_download_times_value_is_missing(self) -> None:
        detail = parse_vjshi_work_detail(
            """
            <html>
              <body>
                <script>window.__data = [\"downloadTimes\",\"entityType\",\"NP\"];</script>
                <section>素材详情 素材标题 测试素材 上传日期 2023-06-12 点击 3,807次 购买 120次</section>
              </body>
            </html>
            """,
            {"work_id": "download-4", "work_url": "https://www.vjshi.com/watch/24324889.html"},
        )
        self.assertEqual(detail["download_count"], 120)

    def test_fetch_single_work_uses_detail_parser_and_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "work.json"
            with patch("ai_video_asset_skill.market_mining._fetch_url", return_value=DETAIL_HTML):
                detail = fetch_vjshi_work_detail(
                    "https://www.vjshi.com/watch/123456.html?from=search",
                    output_json=output,
                    search_keyword="深圳",
                )
            self.assertEqual(detail["work_id"], "123456")
            self.assertEqual(detail["search_keyword"], "深圳")
            self.assertTrue(output.exists())
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(saved["work_url"], "https://www.vjshi.com/watch/123456.html")

    def test_fetch_batch_writes_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "works.jsonl"
            urls = "https://www.vjshi.com/watch/123456.html,https://www.vjshi.com/watch/222333.html"
            with patch("ai_video_asset_skill.market_mining._fetch_url", return_value=DETAIL_HTML):
                batch = fetch_vjshi_work_details_batch(
                    urls=urls,
                    output_jsonl=output,
                    search_keyword="中秋节",
                    delay_seconds=0,
                )
            self.assertEqual(batch["requested_count"], 2)
            self.assertEqual(batch["success_count"], 2)
            self.assertEqual(batch["error_count"], 0)
            lines = output.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            self.assertEqual(json.loads(lines[0])["search_keyword"], "中秋节")

    def test_fetch_search_results_writes_work_urls(self) -> None:
        self.assertIn("categoryIdForSoftware=230", build_vjshi_keyword_search_url("机器人"))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "search.jsonl"
            with patch("ai_video_asset_skill.vjshi_search._fetch_url", return_value=SEARCH_HTML):
                result = fetch_vjshi_search_results(
                    keyword="机器人",
                    limit=10,
                    output_jsonl=output,
                )
            self.assertEqual(result["result_count"], 2)
            self.assertEqual(result["work_urls"][0], "https://www.vjshi.com/watch/123456.html")
            self.assertEqual(json.loads(output.read_text(encoding="utf-8").splitlines()[0])["work_id"], "123456")

    def test_parse_work_detail_prefers_material_detail_fields(self) -> None:
        html = """
        <html>
          <script type="application/ld+json">
          {"@context":"https://schema.org","@type":"VideoObject","name":"中秋节月亮_视频素材下载",
           "uploadDate":"2025-09-17T22:43:38","author":{"@type":"Person","name":"AgiAgu"},
            "duration":"PT15M","contentUrl":"https://mp4.vjshi.com/preview.mp4",
           "interactionStatistic":{"@type":"InteractionCounter","userInteractionCount":2852}}
          </script>
          <body>
            <span>88购买</span>
            <section>素材详情 素材标题 中秋节月亮 素材编号 39435526 透明通道 不支持 无缝循环 不支持
            素材类型 视频素材 AIGC说明 本作品包含AI生成内容或全部为AI生成 文件大小 2.1G 上传日期 2025-09-17
            点击 2,852次 购买 119次 1分53秒以前为快速预览，后面为正常速度。</section>
            <section>素材配乐</section>
          </body>
        </html>
        """
        detail = parse_vjshi_work_detail(html, {"work_id": "39435526"})
        self.assertEqual(detail["title"], "中秋节月亮")
        self.assertEqual(detail["purchase_count"], 119)
        self.assertEqual(detail["click_count"], 2852)
        self.assertEqual(detail["file_size"], "2.1G")
        self.assertEqual(detail["duration"], "15分钟")
        self.assertEqual(detail["author"], "AgiAgu")
        self.assertEqual(detail["material_type"], "视频素材")

    def test_market_search_url_defaults_to_video_material_filter(self) -> None:
        url = build_vjshi_search_url("新能源汽车")
        self.assertIn("/so?", url)
        self.assertIn("categoryIdForSoftware=230", url)
        self.assertIn("st=y", url)
        all_media_url = build_vjshi_search_url("新能源汽车", video_material_only=False)
        self.assertIn("/search?", all_media_url)
        self.assertNotIn("categoryIdForSoftware=230", all_media_url)

    def test_keyword_analysis_creates_traceable_buyer_prompts(self) -> None:
        detail = parse_vjshi_work_detail(
            DETAIL_HTML,
            {
                "work_id": "123456",
                "search_keyword": "端午 龙舟",
                "purchase_count": 286,
                "work_url": "https://www.vjshi.com/watch/123456.html",
            },
        )
        analysis = analyze_market_keywords("端午节 AI 视频素材", ["端午节", "赛龙舟", "粽子"], [detail], [])
        prompts = analysis["buyer_search_prompts"]
        self.assertTrue(any("龙舟" in item["prompt"] for item in prompts))
        self.assertTrue(all(item["evidence_work_ids"] for item in prompts[:1]))
        self.assertIn("camera_terms", analysis["keyword_analysis"]["classified_terms"])

    def test_business_signing_topic_does_not_fall_into_city_directions(self) -> None:
        details = [
            {
                "work_id": "biz-1",
                "title": "高端商务合作握手视频",
                "search_keyword": "商务握手",
                "detail_keywords": ["商务握手", "商务合作", "签约", "合作握手", "成功人士", "企业宣传片"],
                "purchase_count": 381,
                "click_count": 9000,
                "material_income": 12000,
                "work_url": "https://www.vjshi.com/watch/29004997.html",
            },
            {
                "work_id": "biz-2",
                "title": "商务签约 合作握手",
                "search_keyword": "签约成功",
                "detail_keywords": ["商务签约", "签字", "战略合作", "会议室", "写字楼"],
                "purchase_count": 234,
                "click_count": 6000,
                "material_income": 8000,
                "work_url": "https://www.vjshi.com/watch/26434145.html",
            },
        ]

        analysis = analyze_market_keywords(
            "商务人士 签约成功 合作握手 商务素材 宣传片",
            ["商务握手", "签约成功", "合作签约"],
            details,
            [],
            use_market_signals=False,
        )

        prompts = [item["prompt"] for item in analysis["buyer_search_prompts"]]
        directions = [item["direction_name"] for item in analysis["commercial_ai_directions"]]
        self.assertTrue(any("商务" in prompt or "签约" in prompt or "握手" in prompt for prompt in prompts))
        self.assertTrue(any("商务签约" in direction or "合作握手" in direction for direction in directions))
        self.assertFalse(any("AI视频素材" in prompt or "商务素材" in prompt for prompt in prompts))
        self.assertFalse(any("AI视频素材" in direction or "商务素材" in direction for direction in directions))
        self.assertFalse(any("深圳" in prompt for prompt in prompts))
        self.assertFalse(any("深圳" in direction for direction in directions))
        self.assertFalse(any("端午" in prompt or "粽子" in prompt for prompt in prompts))
        self.assertFalse(any("端午" in direction or "粽子" in direction for direction in directions))

    def test_business_signing_second_pass_expands_related_directions(self) -> None:
        details = [
            {
                "work_id": "biz-1",
                "title": "商务人士 签约成功 合作握手",
                "search_keyword": "商务签约",
                "detail_keywords": ["商务签约", "合作握手", "商务洽谈", "合同", "会议室", "合作共赢"],
                "purchase_count": 943,
                "material_income": 123000,
                "work_url": "https://www.vjshi.com/watch/27723278.html",
            },
            {
                "work_id": "biz-2",
                "title": "高端商务合作 签约 握手",
                "search_keyword": "合作握手",
                "detail_keywords": ["高端商务", "战略合作", "商务谈判", "签字", "写字楼"],
                "purchase_count": 665,
                "material_income": 85000,
                "work_url": "https://www.vjshi.com/watch/24306021.html",
            },
        ]

        analysis = analyze_market_keywords(
            "商务人士 签约成功 合作握手 商务宣传片素材",
            ["商务签约", "合作握手", "签约仪式", "企业合作", "成功签约"],
            details,
            [],
            use_market_signals=False,
        )

        prompts = [item["prompt"] for item in analysis["buyer_search_prompts"]]
        joined = " ".join(prompts)

        self.assertIn("商务洽谈 签约", joined)
        self.assertIn("合同签约 握手", joined)
        self.assertIn("会议室 商务合作", joined)
        self.assertTrue(any("战略合作" in prompt or "高端商务" in prompt for prompt in prompts))
        self.assertTrue(all("宣传片" not in prompt and "素材" not in prompt for prompt in prompts))

    def test_science_lab_topic_does_not_use_business_signing_prompts(self) -> None:
        details = [
            {
                "work_id": "lab-1",
                "title": "4k科研人员操作仪器材料测试材料拉伸试验",
                "search_keyword": "材料实验室",
                "detail_keywords": ["新材料", "科研", "实验室", "科研人员", "材料测试", "仪器", "样品"],
                "purchase_count": 1,
                "work_url": "https://www.vjshi.com/watch/100.html",
            },
            {
                "work_id": "lab-2",
                "title": "大学科研人员实验室研发团队讨论",
                "search_keyword": "大学科研人员",
                "detail_keywords": ["大学科研", "实验室研发团队", "科研团队", "研究", "实验室"],
                "purchase_count": 2,
                "work_url": "https://www.vjshi.com/watch/101.html",
            },
            {
                "work_id": "noise-1",
                "title": "商务合作握手宣传片",
                "search_keyword": "科研团队",
                "detail_keywords": ["商务", "合作", "握手", "签约", "宣传片"],
                "purchase_count": 900,
                "work_url": "https://www.vjshi.com/watch/102.html",
            },
        ]

        analysis = analyze_market_keywords(
            "新材料科研团队 实验室研发团队 大学科研人员 商务宣传片素材",
            ["新材料科研", "实验室研发团队", "大学科研人员", "科研团队", "材料实验室"],
            details,
            [],
            use_market_signals=False,
        )

        prompts = [item["prompt"] for item in analysis["buyer_search_prompts"]]
        joined = " ".join(prompts)
        self.assertTrue(any("科研" in prompt or "实验室" in prompt or "材料" in prompt for prompt in prompts))
        self.assertNotIn("商务握手", joined)
        self.assertNotIn("签约成功", joined)
        self.assertNotIn("合作签约", joined)
        self.assertNotIn("商务洽谈", joined)
        self.assertNotIn("商务宣传片素材", joined)
        self.assertNotIn("宣传片", joined)
        self.assertNotIn("素材", joined)

    def test_detail_rows_are_balanced_by_search_keyword(self) -> None:
        rows = [
            {"work_id": f"a-{index}", "search_keyword": "商务握手"}
            for index in range(3)
        ] + [
            {"work_id": f"b-{index}", "search_keyword": "签约成功"}
            for index in range(2)
        ]

        selected = _select_detail_rows(rows, limit=2, balanced_by_search_keyword=True)
        selected_ids = [row["work_id"] for row in selected]

        self.assertEqual(selected_ids, ["a-0", "a-1", "b-0", "b-1"])

    def test_dedupe_works_keeps_all_matched_search_keywords(self) -> None:
        rows = [
            {
                "work_id": "29004997",
                "work_url": "https://www.vjshi.com/watch/29004997.html",
                "search_keyword": "商务握手",
                "source_search_url": "https://www.vjshi.com/search?wd=a",
                "rank": 2,
            },
            {
                "work_url": "https://www.vjshi.com/watch/29004997.html",
                "search_keyword": "签约成功",
                "source_search_url": "https://www.vjshi.com/search?wd=b",
                "rank": 5,
            },
        ]

        deduped = _dedupe_works(rows)

        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["work_id"], "29004997")
        self.assertEqual(deduped[0]["duplicate_search_count"], 2)
        self.assertEqual(deduped[0]["matched_search_keywords"], ["商务握手", "签约成功"])
        self.assertEqual(len(deduped[0]["source_ranks"]), 2)

    def test_second_pass_prompt_gate_rejects_off_topic_festival_terms(self) -> None:
        prompts = [
            {
                "prompt": "商务握手",
                "direction_name": "商务签约成功与合作握手",
            },
            {
                "prompt": "端午 礼盒 电商",
                "direction_name": "无品牌礼盒与节日促销场景",
            },
            {
                "prompt": "商务握手 礼盒 无品牌",
                "direction_name": "无品牌礼盒与节日促销场景",
            },
        ]

        accepted, rejected = _filter_topic_relevant_buyer_prompts(
            prompts,
            "商务人士 签约成功 合作握手 商务素材 宣传片",
            ["商务握手", "签约成功", "合作签约"],
            [{"search_keyword": "商务握手"}],
        )

        self.assertEqual([item["prompt"] for item in accepted], ["商务握手"])
        self.assertEqual({item["prompt"] for item in rejected}, {"端午 礼盒 电商", "商务握手 礼盒 无品牌"})
        self.assertTrue(all(not item["topic_relevance"]["accepted"] for item in rejected))

    def test_first_pass_keyword_analysis_ignores_market_signals(self) -> None:
        low_signal_relevant = {
            "work_id": "robot-1",
            "title": "robot factory broll",
            "search_keyword": "robot",
            "detail_keywords": ["robot", "factory", "broll"],
            "purchase_count": 1,
            "material_income": 0,
        }
        high_signal_irrelevant = {
            "work_id": "cake-1",
            "title": "cake gift box",
            "search_keyword": "cake",
            "detail_keywords": ["cake", "gift", "box"],
            "purchase_count": 500,
            "material_income": 10000,
        }

        semantic = analyze_market_keywords(
            "robot AI video asset",
            ["robot"],
            [low_signal_relevant, high_signal_irrelevant],
            [],
            use_market_signals=False,
        )
        semantic_scores = {
            row["term"]: row["weighted_score"]
            for row in semantic["keyword_analysis"]["weighted_terms"]
        }

        market = analyze_market_keywords(
            "robot AI video asset",
            ["robot"],
            [low_signal_relevant, high_signal_irrelevant],
            [],
            use_market_signals=True,
        )
        market_scores = {
            row["term"]: row["weighted_score"]
            for row in market["keyword_analysis"]["weighted_terms"]
        }

        self.assertEqual(semantic["keyword_analysis"]["analysis_mode"], "semantic_only")
        self.assertFalse(semantic["keyword_analysis"]["market_signals_used_for_keyword_weighting"])
        self.assertEqual(semantic_scores["robot"], 1)
        self.assertEqual(semantic_scores["cake"], 1)
        self.assertEqual(market["keyword_analysis"]["analysis_mode"], "market_signal_weighted")
        self.assertTrue(market["keyword_analysis"]["market_signals_used_for_keyword_weighting"])
        self.assertGreater(market_scores["cake"], semantic_scores["cake"])

    def test_risky_preview_flags_block_image2_reference(self) -> None:
        score = _score_reference_candidate(
            {
                "title": "端午多宫格预览图 带水印文字",
                "kind": "market_reference",
                "page_url": "https://www.vjshi.com/watch/123456.html",
                "source_page_url": "https://www.vjshi.com/watch/123456.html",
                "purchase_count": 300,
                "keywords": ["端午", "龙舟"],
                "risk_flags": ["multi_panel_preview", "watermark_or_platform_badge", "readable_text"],
            },
            "image/jpeg",
            500_000,
        )
        self.assertFalse(score["can_be_image_reference"])
        self.assertIn("multi_panel_preview", score["reference_risk_flags"])

    def test_mine_market_writes_required_outputs_from_source_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            source = Path(tmp) / "source.json"
            source.write_text(
                json.dumps(
                    {
                        "items": [
                            {
                                "html": SEARCH_HTML,
                                "search_keyword": "端午 龙舟",
                                "page_url": "https://www.vjshi.com/search?wd=x",
                            },
                            {
                                "detail_html": DETAIL_HTML,
                                "work_id": "123456",
                                "work_url": "https://www.vjshi.com/watch/123456.html",
                                "search_keyword": "端午 龙舟",
                                "purchase_count": 286,
                            },
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            result = mine_market(
                project,
                "端午节 AI 视频素材",
                seed_keywords="端午节,赛龙舟,粽子",
                fetch_live=False,
                first_pass_source_json=source,
            )
            self.assertTrue(result["system_output_success"])
            mining_dir = project / "00_调研" / "市场反挖"
            self.assertTrue((mining_dir / "买家搜索提示词.json").exists())
            self.assertTrue((mining_dir / "商业AI方向.json").exists())
            next_step_path = mining_dir / "后续动作确认.json"
            self.assertTrue(next_step_path.exists())
            self.assertEqual(
                result["system_output_recommended_next_action"],
                "ask_user_before_collect_high_value_video_frames",
            )
            self.assertIn("是否继续采集高价值作品", result["system_output_next_step_question"])
            self.assertIn("prepare-high-value-video-frame-queue", "\n".join(result["system_output_next_step_commands"]))
            next_step = json.loads(next_step_path.read_text(encoding="utf-8"))
            self.assertTrue(next_step["confirmation_required"])
            self.assertEqual(next_step["status"], "pending_user_confirmation")
            self.assertTrue(next_step["usage_policy"]["never_download_paid_originals"])
            summary = json.loads((mining_dir / "市场反挖摘要.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["second_pass_query_source"], "买家搜索提示词.json")

    def test_market_mining_project_dir_reuses_same_day_topic_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            created_at = datetime(2026, 6, 26, 13, 59, 29)
            later_at = datetime(2026, 6, 26, 14, 7, 45)
            topic = "商务人士 签约成功 合作握手 宣传片商务素材"
            with patch("ai_video_asset_skill.main_orchestrator.DEFAULT_OUTPUT_ROOT", tmp):
                first = create_market_mining_project_dir(topic, created_at=created_at)
                second = create_market_mining_project_dir(topic, created_at=later_at)

            self.assertEqual(first, second)
            self.assertEqual(len([path for path in Path(tmp).iterdir() if path.is_dir()]), 1)
            self.assertTrue((first / "00_调研").exists())
            self.assertIn("素材调研", first.name)
            self.assertNotIn("market_mining", first.name)

    def test_formal_project_reuses_existing_market_research_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            created_at = datetime(2026, 6, 26, 13, 59, 29)
            topic = "商务人士 签约成功 合作握手 宣传片商务素材"
            with patch("ai_video_asset_skill.main_orchestrator.DEFAULT_OUTPUT_ROOT", tmp):
                market_project = create_market_mining_project_dir(topic, created_at=created_at)

            dirs = create_project_dirs(
                {
                    "user_input_output_root_dir": tmp,
                    "user_input_industry_name": "商务",
                    "user_input_topic_title": topic,
                },
                created_at=datetime(2026, 6, 26, 14, 10, 0),
            )

            self.assertEqual(dirs["project_dir"], market_project)
            self.assertEqual(len([path for path in Path(tmp).iterdir() if path.is_dir()]), 1)
            self.assertTrue((market_project / "01_分镜").exists())


if __name__ == "__main__":
    unittest.main()
