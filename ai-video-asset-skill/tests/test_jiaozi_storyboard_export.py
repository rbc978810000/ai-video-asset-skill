from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ai_video_asset_skill.jiaozi_storyboard_export import audit_jiaozi_storyboard_payload, export_jiaozi_storyboard_script


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


class JiaoziStoryboardExportTests(unittest.TestCase):
    def test_export_jiaozi_storyboard_uses_structured_prompts_and_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            _seed_project(
                project,
                "商务人士 签约成功 合作握手",
                [
                    _frame_analysis("frame_handshake", "握手近景", ["process_action", "detail_closeup"], ["closeup", "depth"]),
                    _frame_analysis("frame_signing", "签署合同", ["process_action", "detail_closeup"], ["closeup", "macro"]),
                    _frame_analysis("frame_meeting", "会议讨论", ["people_usage", "main_subject"], ["medium", "depth"]),
                ],
            )

            result = export_jiaozi_storyboard_script(project, shot_count=6, duration_per_shot=4)
            payload = json.loads(Path(result["system_output_storyboard_script_json"]).read_text(encoding="utf-8"))

            self.assertEqual(payload["shotCount"], 6)
            self.assertEqual(len(payload["referenceAssets"]), 3)
            self.assertTrue(payload["skillMetadata"]["all_selected_reference_frames_preserved"])
            self.assertGreater(payload["skillMetadata"]["unbound_original_shot_count"], 0)
            self.assertEqual(len(payload["storyboard_master"]), 6)
            self.assertEqual(len(payload["reference_image_plan"]["items"]), 6)
            self.assertTrue(all(item["reference_role"] in {"standalone", "anchor", "derived_view"} for item in payload["reference_image_plan"]["items"]))
            self.assertTrue(all(item["reference_shot_id"] is None for item in payload["reference_image_plan"]["items"] if item["reference_role"] != "derived_view"))
            opening_titles = [
                shot["shot_title"]
                for shot in payload["storyboard_master"]
                if shot["scene_group"] == "01_开场建立"
            ]
            self.assertTrue(all("结尾" not in title and "收尾" not in title for title in opening_titles))
            used_ids = {
                item["market_reference_asset_ids"][0]
                for item in payload["reference_image_plan"]["items"]
                if item["market_reference_asset_ids"]
            }
            self.assertGreaterEqual(len(used_ids), 1)
            self.assertTrue(used_ids.issubset({asset["id"] for asset in payload["referenceAssets"]}))
            self.assertTrue(any(not item["market_reference_asset_ids"] for item in payload["reference_image_plan"]["items"]))
            self.assertTrue(payload["referenceAssets"][0]["url"].startswith("file:///"))
            self.assertTrue(Path(payload["referenceAssets"][0]["sourcePath"]).exists())
            self.assertIn("shot_role_tags", payload["referenceAssets"][0]["metadata"])
            self.assertIn("reuse_budget", payload["referenceAssets"][0]["metadata"])
            self.assertIn("model_reference_instruction", payload["referenceAssets"][0]["metadata"])
            self.assertIn("reference_reuse_policy", payload["skillMetadata"])

            image_prompt = payload["storyboard_master"][0]["imagePrompt"]
            self.assertTrue(image_prompt.startswith("生成图片：\n"))
            self.assertIn("\n参考图使用：", image_prompt)
            self.assertIn("\n整体质感：", image_prompt)
            self.assertIn("\n不要出现：", image_prompt)
            self.assertIn("storyboard_lane", payload["storyboard_master"][0])
            self.assertIn("storyboard_lane", payload["reference_image_plan"]["items"][0])
            self.assertNotIn("画面 brief", image_prompt)
            self.assertNotIn("补充要求", image_prompt)
            self.assertNotIn("复用预算", image_prompt)
            self.assertNotIn("参考图主体关系", image_prompt)
            self.assertNotIn("不要出现：不要出现", image_prompt)
            bound_prompt = next(
                shot["imagePrompt"]
                for shot in payload["storyboard_master"]
                if shot["reference_frame_ids"]
            )
            self.assertIn("参考这张图", bound_prompt)

            video_prompt = payload["storyboard_master"][0]["videoPrompt"]
            self.assertTrue(video_prompt.startswith("从当前画面开始，"))
            self.assertNotIn("镜头时长", video_prompt)
            self.assertNotIn("视频运镜：", video_prompt)
            self.assertNotIn("主体动态：", video_prompt)
            self.assertNotIn("场景动画：", video_prompt)
            self.assertNotIn("参考帧动态潜力", video_prompt)
            self.assertNotIn("核心主体自然进入视觉中心", video_prompt)
            self.assertNotIn("只表现一个清楚的商务动作瞬间", video_prompt)

    def test_business_opening_does_not_become_repeated_handshake_windows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            _seed_project(
                project,
                "商务人士 签约成功 合作握手 商务宣传片素材",
                [
                    _frame_analysis(
                        "frame_handshake_closeup",
                        "窗边商务握手近景，双手局部和深色西装袖口",
                        ["process_action", "detail_closeup"],
                        ["closeup", "depth"],
                        weight=0.96,
                        topic_fit=96,
                    ),
                    _frame_analysis(
                        "frame_signing_detail",
                        "签字笔落在合同纸面上的微距局部",
                        ["process_action", "detail_closeup"],
                        ["closeup", "macro"],
                        weight=0.92,
                        topic_fit=90,
                    ),
                    _frame_analysis(
                        "frame_business_building",
                        "现代城市商务楼宇玻璃幕墙宽幅空间",
                        ["establishing"],
                        ["wide", "city", "copy_space"],
                        weight=0.9,
                        topic_fit=88,
                    ),
                    _frame_analysis(
                        "frame_meeting_room_empty",
                        "明亮会议室空镜、长桌、窗景和玻璃反射",
                        ["establishing", "transition_mood"],
                        ["wide", "office", "reflection", "depth"],
                        weight=0.88,
                        topic_fit=86,
                    ),
                ],
            )

            result = export_jiaozi_storyboard_script(project, shot_count=20, duration_per_shot=4)
            payload = json.loads(Path(result["system_output_storyboard_script_json"]).read_text(encoding="utf-8"))

            opening_shots = [
                shot
                for shot in payload["storyboard_master"]
                if shot["scene_group"] == "01_开场建立"
            ]
            self.assertGreaterEqual(len(opening_shots), 2)
            for shot in opening_shots:
                opening_text = " ".join(
                    [shot["shot_title"], shot["subject_main"], shot["action_description"], shot["imagePrompt"]]
                )
                self.assertNotIn("握手", opening_text)
                self.assertNotIn("签约成功", opening_text)

            opening_plan_items = [
                item
                for item in payload["reference_image_plan"]["items"]
                if item["scene_group"] == "01_开场建立" and item["reference_frame_ids"]
            ]
            self.assertTrue(opening_plan_items)
            for item in opening_plan_items:
                self.assertNotIn("frame_handshake_closeup", item["reference_frame_ids"])
                self.assertNotEqual(item["reference_usage_role"], "action_pose")

    def test_high_value_reference_reuse_builds_anchor_then_derived_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            _seed_project(
                project,
                "商务会议 合作握手 高端宣传片素材",
                [
                    _frame_analysis(
                        "frame_meeting_hero",
                        "双方团队围绕会议桌讨论合作方案的宽幅会议室空间",
                        ["process_action", "people_usage"],
                        ["wide", "depth", "medium"],
                        weight=0.96,
                        topic_fit=96,
                    ),
                    _frame_analysis(
                        "frame_pen_detail",
                        "签字笔与纸面微距特写",
                        ["detail_closeup"],
                        ["closeup", "macro"],
                        weight=0.92,
                        topic_fit=88,
                    ),
                    _frame_analysis(
                        "frame_watermark",
                        "带水印和可读文字的会议截图",
                        ["people_usage"],
                        ["medium"],
                        risk_flags=["水印风险", "文字风险"],
                        weight=0.95,
                        topic_fit=90,
                    ),
                ],
            )

            result = export_jiaozi_storyboard_script(project, shot_count=18, duration_per_shot=4)
            payload = json.loads(Path(result["system_output_storyboard_script_json"]).read_text(encoding="utf-8"))
            items = payload["reference_image_plan"]["items"]
            frame_counts: dict[str, int] = {}
            for item in items:
                self.assertIn(item["reference_role"], {"standalone", "anchor", "derived_view"})
                for frame_id in [*item.get("reference_frame_ids", []), *item.get("inherited_reference_frame_ids", [])]:
                    frame_counts[frame_id] = frame_counts.get(frame_id, 0) + 1
                if item.get("reference_frame_ids") or item.get("inherited_reference_frame_ids"):
                    self.assertIn("reference_usage_role", item)
                    self.assertIn("reference_reuse_group", item)
                    self.assertIn("reference_reuse_budget", item)

            self.assertGreaterEqual(frame_counts.get("frame_meeting_hero", 0), 2)
            self.assertLessEqual(max(frame_counts.values()), 3)
            self.assertEqual(frame_counts.get("frame_watermark", 0), 0)
            anchors = [item for item in items if item["reference_role"] == "anchor"]
            derived = [item for item in items if item["reference_role"] == "derived_view"]
            self.assertTrue(anchors)
            self.assertTrue(derived)
            anchor_ids = {item["shot_id"] for item in anchors}
            for item in derived:
                self.assertIn(item["reference_shot_id"], anchor_ids)
                self.assertFalse(item["market_reference_asset_ids"])
                self.assertFalse(item["reference_frame_ids"])
                self.assertTrue(item["inherited_reference_frame_ids"])
                shot = next(shot for shot in payload["storyboard_master"] if shot["shot_id"] == item["shot_id"])
                self.assertIn("锚点图", shot["imagePrompt"])
                self.assertNotIn("参考这张图", shot["imagePrompt"])
            asset_by_frame = {asset["metadata"]["frame_id"]: asset for asset in payload["referenceAssets"]}
            self.assertEqual(asset_by_frame["frame_meeting_hero"]["metadata"]["reuse_budget"], 3)
            self.assertEqual(asset_by_frame["frame_watermark"]["metadata"]["reuse_budget"], 0)

    def test_non_business_topic_keeps_global_style_visual_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            _seed_project(
                project,
                "端午节 粽子 礼盒 节日视频素材",
                [
                    _frame_analysis("frame_table", "节日餐桌宽幅建立", ["establishing"], ["wide", "copy_space"]),
                    _frame_analysis("frame_zongzi", "粽子与礼盒细节特写", ["detail_closeup", "main_subject"], ["closeup", "macro"]),
                    _frame_analysis("frame_family", "人物分享节日礼盒", ["people_usage", "outcome_emotion"], ["medium"]),
                    _frame_analysis("frame_light", "暖色节日光影留白", ["transition_mood", "end_copy_space"], ["copy_space", "reflection"]),
                ],
            )

            result = export_jiaozi_storyboard_script(project, shot_count=8, duration_per_shot=4)
            payload = json.loads(Path(result["system_output_storyboard_script_json"]).read_text(encoding="utf-8"))

            self.assertEqual(payload["skillMetadata"]["topic_profile"]["domain"], "festival")
            global_style = payload["globalStyle"]
            for concrete_word in ["粽子", "礼盒", "商务人士", "西装", "合同", "会议室"]:
                self.assertNotIn(concrete_word, global_style)
            self.assertIn("商业", global_style)
            self.assertIn("16:9", global_style)

            video_prompts = [shot["videoPrompt"] for shot in payload["storyboard_master"][:4]]
            self.assertGreater(len(set(video_prompts)), 1)
            self.assertTrue(all("镜头时长" not in prompt for prompt in video_prompts))
            self.assertTrue(all("西装" not in prompt and "合同" not in prompt for prompt in video_prompts))

    def test_new_energy_vehicle_road_prompt_does_not_mix_business_entry_motion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            _seed_project(
                project,
                "新能源汽车 智能驾驶 智慧出行 充电桩 动力电池 AI适配素材包",
                [
                    _frame_analysis("frame_road", "新能源车在城市道路自动驾驶，车道线和前车关系清楚", ["process_action", "main_subject"], ["medium", "depth"]),
                    _frame_analysis("frame_charging", "现代充电站内车辆连接充电枪", ["process_action", "detail_closeup"], ["medium", "depth"]),
                    _frame_analysis("frame_battery", "动力电池包和电芯排列的洁净工业特写", ["detail_closeup"], ["closeup", "macro"]),
                    _frame_analysis("frame_factory", "新能源汽车工厂机械臂装配车身", ["establishing", "process_action"], ["wide", "depth"]),
                ],
            )

            result = export_jiaozi_storyboard_script(project, shot_count=20, duration_per_shot=4)
            payload = json.loads(Path(result["system_output_storyboard_script_json"]).read_text(encoding="utf-8"))
            road_shot = next(shot for shot in payload["storyboard_master"] if "车辆智能巡航" in shot["shot_title"])
            combined_prompt = road_shot["imagePrompt"] + road_shot["videoPrompt"]

            for bad_word in ["商务人士", "会议区域", "手持文件", "合同", "会议桌", "桌面道具"]:
                self.assertNotIn(bad_word, combined_prompt)
            self.assertIn("车道", road_shot["videoPrompt"])
            self.assertIn("前车", road_shot["videoPrompt"])

            road_shot["videoPrompt"] = (
                "从当前画面开始，保持当前新能源车在道路上保持车道并识别前车的纵深透视。"
                "平视中景缓慢后退，让商务人士自然进入画面并靠近会议区域；"
                "商务人士以克制步伐进入或穿过空间，手持文件保持稳定。"
            )
            audited = audit_jiaozi_storyboard_payload(payload, auto_fix=True)
            fixed_road_shot = next(
                shot for shot in audited["payload"]["storyboard_master"] if shot["shot_id"] == road_shot["shot_id"]
            )

            self.assertGreaterEqual(audited["summary"]["fixed_count"], 1)
            self.assertNotIn("商务人士", fixed_road_shot["videoPrompt"])
            self.assertNotIn("会议区域", fixed_road_shot["videoPrompt"])
            self.assertIn("车道", fixed_road_shot["videoPrompt"])

    def test_establishing_shot_prefers_spatial_reference_over_detail_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            _seed_project(
                project,
                "工业自动化产线 商业视频素材",
                [
                    _frame_analysis("frame_detail", "设备按钮和金属结构特写", ["detail_closeup"], ["closeup", "macro"]),
                    _frame_analysis("frame_factory_wide", "现代工厂产线宽幅空间", ["establishing"], ["wide", "depth"]),
                ],
            )

            result = export_jiaozi_storyboard_script(project, shot_count=8, duration_per_shot=4)
            payload = json.loads(Path(result["system_output_storyboard_script_json"]).read_text(encoding="utf-8"))

            first_reference = payload["storyboard_master"][0]["reference_frame_ids"][0]
            self.assertEqual(first_reference, "frame_factory_wide")
            self.assertIn("01_开场建立", payload["storyboard_master"][0]["scene_group"])

    def test_storyboard_audit_unbinds_conflicting_reference_and_video_motion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            _seed_project(
                project,
                "商务人士 签约成功 合作握手 商务宣传片素材",
                [
                    _frame_analysis(
                        "frame_signing_detail",
                        "签字笔落在合同纸面上的微距局部",
                        ["detail_closeup"],
                        ["closeup", "macro"],
                    )
                ],
            )
            result = export_jiaozi_storyboard_script(project, shot_count=1, duration_per_shot=4)
            payload = json.loads(Path(result["system_output_storyboard_script_json"]).read_text(encoding="utf-8"))
            shot = payload["storyboard_master"][0]
            asset = payload["referenceAssets"][0]
            shot["reference_frame_ids"] = ["frame_signing_detail"]
            shot["reference_frame_paths"] = [asset["sourcePath"]]
            shot["reference_dependency"]["reference_frame_ids"] = ["frame_signing_detail"]
            shot["reference_dependency"]["reference_frame_paths"] = [asset["sourcePath"]]
            shot["reference_dependency"]["reference_image_path"] = asset["sourcePath"]
            shot["imagePrompt"] = shot["imagePrompt"].replace("本镜头不使用具体参考图", "参考这张图")
            shot["videoPrompt"] = "从当前画面开始，商务人士握手并围绕会议桌移动。"
            plan_item = payload["reference_image_plan"]["items"][0]
            plan_item["reference_frame_ids"] = ["frame_signing_detail"]
            plan_item["reference_frame_paths"] = [asset["sourcePath"]]
            plan_item["reference_image_path"] = asset["sourcePath"]

            audited = audit_jiaozi_storyboard_payload(payload, auto_fix=True)
            fixed = audited["payload"]
            fixed_shot = fixed["storyboard_master"][0]

            self.assertEqual(audited["summary"]["fixed_count"], 1)
            self.assertEqual(fixed_shot["reference_frame_ids"], [])
            self.assertIn("本镜头不使用具体参考图", fixed_shot["imagePrompt"])
            self.assertNotIn("握手", fixed_shot["videoPrompt"])
            self.assertEqual(fixed["reference_image_plan"]["items"][0]["reference_frame_ids"], [])


def _seed_project(project: Path, topic: str, analyses: list[dict]) -> None:
    frame_dir = project / "00_调研" / "精选参考帧" / "帧图片"
    frame_dir.mkdir(parents=True)
    frames = []
    for index, analysis in enumerate(analyses, start=1):
        image_path = frame_dir / f"精选帧_{index:04d}.png"
        image_path.write_bytes(PNG_1X1)
        frames.append(
            {
                "frame_id": analysis["frame_id"],
                "selected_frame_path": str(image_path),
                "original_frame_path": str(image_path),
                "selected_frame_relative_path": f"00_调研/精选参考帧/帧图片/精选帧_{index:04d}.png",
            }
        )
    _write_json(project / "项目清单.json", {"project_title": topic})
    _write_json(project / "00_调研" / "精选参考帧" / "精选参考帧清单.json", {"frames": frames})
    _write_json(project / "00_调研" / "精选参考帧" / "参考帧分析.json", {"frames": analyses})


def _frame_analysis(
    frame_id: str,
    visual_summary: str,
    role_tags: list[str],
    composition_tags: list[str],
    *,
    weight: float = 0.9,
    topic_fit: int = 90,
    risk_flags: list[str] | None = None,
    policy: str = "image2_reference",
) -> dict:
    return {
        "frame_id": frame_id,
        "sheet_label": f"#{frame_id}",
        "ai_prompt_analysis": (
            f"主体：{visual_summary}\n"
            "背景：真实商业素材场景\n"
            "构图：横向16:9画面，主体关系清楚\n"
            "视角/镜头：平视真实摄影镜头，景深自然\n"
            "光线：柔和自然光，明暗关系克制\n"
            "色彩：干净高级色调\n"
            "风格：真实摄影商业素材\n"
            "材质与细节：主体纹理、环境层次和局部细节清楚\n"
            "情绪氛围：专业可信\n\n"
            "【中文生图提示词】\n"
            f"{visual_summary}，横向16:9真实摄影画面。\n\n"
            "【负面提示词】\n"
            "不要出现：文字、Logo、水印。"
        ),
        "visual_summary": visual_summary,
        "subject_type": "核心主体",
        "scene_type": "真实商业素材场景",
        "shot_role_tags": role_tags,
        "composition_tags": composition_tags,
        "motion_potential": "适合稳定微推或轻微横移。",
        "commercial_use_cases": ["商业素材参考"],
        "topic_fit_score": topic_fit,
        "image2_usage_weight": weight,
        "reference_use_policy": policy,
        "risk_flags": risk_flags or [],
        "prompt_ready_brief": visual_summary,
        "negative_prompt_notes": ["文字", "Logo", "水印"],
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
