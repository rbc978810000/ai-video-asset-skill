from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ai_video_asset_skill.reference_frame_assets import (
    _sample_integrity_report,
    build_reference_frame_binding_plan,
    build_selected_reference_frames,
    collect_high_value_video_frames,
    select_high_value_video_works,
)


PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


class ReferenceFrameAssetTests(unittest.TestCase):
    def test_select_high_value_video_works_takes_top_10_with_preview(self) -> None:
        details = []
        for index in range(12):
            details.append(
                {
                    "work_id": str(index),
                    "work_url": f"https://www.vjshi.com/watch/{index}.html",
                    "preview_video_url": f"https://cdn.example.com/{index}.mp4",
                    "material_type": "视频素材",
                    "material_income": index,
                    "purchase_count": index * 2,
                    "click_count": index * 10,
                }
            )
        details.append({"work_id": "no-preview", "title": "missing source"})

        rows = select_high_value_video_works(details, max_works=10)

        self.assertEqual(len(rows), 10)
        self.assertEqual(rows[0]["work_id"], "11")
        self.assertNotIn("no-preview", {row["work_id"] for row in rows})

    def test_select_high_value_video_works_rejects_templates(self) -> None:
        details = [
            {
                "work_id": "template-1",
                "title": "新能源汽车片头AE模版",
                "work_url": "https://www.vjshi.com/watch/1.html",
                "preview_video_url": "https://cdn.example.com/1.mp4",
                "material_type": "模板素材",
                "src_file_type": "TEMPLATE",
                "material_income": 999999,
            },
            {
                "work_id": "video-1",
                "title": "新能源汽车充电桩实拍",
                "work_url": "https://www.vjshi.com/watch/2.html",
                "preview_video_url": "https://cdn.example.com/2.mp4",
                "material_type": "视频素材",
                "src_file_type": "VIDEO",
                "material_income": 10,
            },
        ]

        rows = select_high_value_video_works(details, max_works=10)

        self.assertEqual([row["work_id"] for row in rows], ["video-1"])

    def test_select_high_value_video_works_rejects_off_topic_when_topic_terms_are_provided(self) -> None:
        details = [
            {
                "work_id": "biz-1",
                "title": "合作签约实拍素材AI美化商务握手交流谈判",
                "work_url": "https://www.vjshi.com/watch/1.html",
                "preview_video_url": "https://cdn.example.com/1.mp4",
                "material_type": "视频素材",
                "material_income": 999999,
            },
            {
                "work_id": "nev-1",
                "title": "新能源汽车充电桩实拍",
                "work_url": "https://www.vjshi.com/watch/2.html",
                "preview_video_url": "https://cdn.example.com/2.mp4",
                "material_type": "视频素材",
                "material_income": 10,
            },
        ]

        rows = select_high_value_video_works(details, max_works=10, topic_terms=["新能源汽车", "充电桩"])

        self.assertEqual([row["work_id"] for row in rows], ["nev-1"])

    def test_collect_high_value_video_frames_uses_configured_workers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            details_path = project / "00_调研" / "市场反挖" / "光厂第二轮作品详情.jsonl"
            details_path.parent.mkdir(parents=True)
            details = [
                {
                    "work_id": str(index),
                    "work_url": f"https://www.vjshi.com/watch/{index}.html",
                    "preview_video_url": f"https://cdn.example.com/{index}.mp4",
                    "material_type": "视频素材",
                    "material_income": 100 - index,
                }
                for index in range(4)
            ]
            details_path.write_text(
                "\n".join(json.dumps(item, ensure_ascii=False) for item in details),
                encoding="utf-8",
            )

            def fake_collect(source_url: str, **kwargs: object) -> dict:
                return {
                    "system_output_success": True,
                    "source_url": source_url,
                    "rebuild_aggregate": kwargs.get("rebuild_aggregate"),
                }

            with patch(
                "ai_video_asset_skill.reference_frame_assets.collect_scene_reference_frames",
                side_effect=fake_collect,
            ) as collect_mock:
                result = collect_high_value_video_frames(project, max_works=4, workers=3, watermark_device="cuda")

            self.assertEqual(result["system_output_workers"], 3)
            self.assertEqual(result["system_output_collected_count"], 4)
            self.assertEqual(collect_mock.call_count, 4)
            for call in collect_mock.call_args_list:
                self.assertIs(call.kwargs["rebuild_aggregate"], False)
                self.assertEqual(call.kwargs["watermark_device"], "cuda")
                self.assertEqual(call.kwargs["threshold"], 0.28)
                self.assertEqual(call.kwargs["min_scene_duration"], 0.6)

    def test_collect_high_value_video_frames_supplements_until_frame_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            details_path = project / "00_调研" / "市场反挖" / "光厂第二轮作品详情.jsonl"
            details_path.parent.mkdir(parents=True)
            details = [
                {
                    "work_id": str(index),
                    "work_url": f"https://www.vjshi.com/watch/{index}.html",
                    "preview_video_url": f"https://cdn.example.com/{index}.mp4",
                    "material_type": "视频素材",
                    "material_income": 1000 - index,
                    "purchase_count": 100 - index,
                    "click_count": 1000 - index,
                }
                for index in range(30)
            ]
            details_path.write_text(
                "\n".join(json.dumps(item, ensure_ascii=False) for item in details),
                encoding="utf-8",
            )

            def fake_collect(source_url: str, **kwargs: object) -> dict:
                return {
                    "system_output_success": True,
                    "system_output_source_id": Path(source_url).stem,
                    "system_output_frame_count": 10,
                }

            aggregate_results = [
                {"frame_count": 0, "manifest_path": project / "manifest.json", "gallery_path": project / "gallery.md"},
                {"frame_count": 100, "manifest_path": project / "manifest.json", "gallery_path": project / "gallery.md"},
                {"frame_count": 320, "manifest_path": project / "manifest.json", "gallery_path": project / "gallery.md"},
                {"frame_count": 320, "manifest_path": project / "manifest.json", "gallery_path": project / "gallery.md"},
            ]

            with patch(
                "ai_video_asset_skill.reference_frame_assets.collect_scene_reference_frames",
                side_effect=fake_collect,
            ) as collect_mock, patch(
                "ai_video_asset_skill.reference_frame_assets._rebuild_aggregate_manifest",
                side_effect=aggregate_results,
            ):
                result = collect_high_value_video_frames(
                    project,
                    initial_works=10,
                    min_total_frames=300,
                    max_works=30,
                    workers=6,
                )

            self.assertEqual(collect_mock.call_count, 20)
            self.assertEqual(result["system_output_final_work_count"], 20)
            self.assertEqual(result["system_output_supplemental_work_count"], 10)
            self.assertEqual(result["system_output_total_frame_count"], 320)
            self.assertEqual(result["system_output_stop_reason"], "reached_min_total_frames")

    def test_sample_integrity_reads_duration_seconds_from_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            manifest_path = project / "source" / "来源信息.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "video_info": {"duration_seconds": 56.0},
                        "source_type": "direct_video_url",
                        "resolved_video_url": "https://cdn.example.com/sample.mp4",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            report = _sample_integrity_report(
                {"declared_duration_seconds": 55},
                {"system_output_manifest": str(manifest_path)},
                project,
            )

            self.assertEqual(report["status"], "ok")
            self.assertEqual(report["actual_downloaded_duration_seconds"], 56.0)
            self.assertGreater(report["duration_ratio"], 1)

    def test_selected_reference_frames_copy_only_operator_selected_and_create_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            frame_dir = project / "00_调研" / "视频参考帧" / "来源" / "来源1"
            frame_dir.mkdir(parents=True)
            source_image = frame_dir / "frame_a.png"
            source_image.write_bytes(PNG_1X1)
            _write_json(
                project / "00_调研" / "视频参考帧" / "视频参考帧清单.json",
                {
                    "assets": [
                        {
                            "frame_id": "frame_a",
                            "source_id": "source1",
                            "path": "00_调研/视频参考帧/来源/来源1/frame_a.png",
                            "quality_score": 88,
                        },
                        {
                            "frame_id": "frame_b",
                            "source_id": "source1",
                            "path": "00_调研/视频参考帧/来源/来源1/missing.png",
                            "quality_score": 77,
                        },
                    ]
                },
            )
            _write_json(
                project / "00_调研" / "市场反挖" / "人工审核.json",
                {"frame_reviews": {"frame_a": {"label": "image2_reference"}, "frame_b": {"label": "excluded"}}},
            )

            result = build_selected_reference_frames(project, max_sheet_items=12)
            selected = json.loads(Path(result["system_output_selected_reference_frames"]).read_text(encoding="utf-8"))
            tasks = json.loads(Path(result["system_output_analysis_tasks"]).read_text(encoding="utf-8"))

            self.assertEqual(selected["selected_count"], 1)
            self.assertEqual(selected["frames"][0]["frame_id"], "frame_a")
            self.assertTrue(Path(selected["frames"][0]["selected_frame_path"]).exists())
            self.assertEqual(tasks["tasks"][0]["frame_ids"], ["frame_a"])
            self.assertIn("visual_summary", tasks["analysis_system_prompt"])
            self.assertIn("image2_usage_weight", tasks["analysis_system_prompt"])
            self.assertIn("reference_use_policy", tasks["analysis_system_prompt"])
            self.assertIn("structured JSON frame object", tasks["tasks"][0]["analysis_instruction"])
            analysis_stub = json.loads(Path(result["system_output_reference_frame_analysis"]).read_text(encoding="utf-8"))
            self.assertIn("prompt_ready_brief", analysis_stub["expected_structured_fields"])

    def test_reference_frame_binding_plan_adds_matching_frame_ids_to_shots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            (project / "01_分镜").mkdir(parents=True)
            _write_json(
                project / "01_分镜" / "分镜总表.json",
                [
                    {
                        "shot_id": "shot_001",
                        "shot_title": "深圳CBD航拍",
                        "scene_group": "深圳CBD",
                        "action_description": "深圳CBD城市天际线航拍",
                    }
                ],
            )
            _write_json(
                project / "00_调研" / "精选参考帧" / "精选参考帧清单.json",
                {
                    "frames": [
                        {
                            "frame_id": "frame_cbd",
                            "selected_frame_path": str(project / "00_调研" / "精选参考帧" / "帧图片" / "精选帧_0001.png"),
                            "commercial_direction": "深圳CBD",
                            "allowed_usage": ["composition_reference"],
                        }
                    ]
                },
            )
            _write_json(
                project / "00_调研" / "精选参考帧" / "参考帧分析.json",
                {"frames": [{"frame_id": "frame_cbd", "scene": "深圳CBD城市天际线", "reference_strength": 9}]},
            )

            result = build_reference_frame_binding_plan(project)
            storyboard = json.loads((project / "01_分镜" / "分镜总表.json").read_text(encoding="utf-8"))
            plan = json.loads(Path(result["system_output_binding_plan"]).read_text(encoding="utf-8"))

            self.assertEqual(storyboard[0]["reference_frame_ids"], ["frame_cbd"])
            self.assertEqual(plan["items"][0]["reference_frame_ids"], ["frame_cbd"])
            self.assertEqual(plan["items"][0]["reference_role"], "standalone")

    def test_reference_frame_binding_plan_does_not_backfill_unmatched_shots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            (project / "01_分镜").mkdir(parents=True)
            _write_json(
                project / "01_分镜" / "分镜总表.json",
                [
                    {
                        "shot_id": "shot_001",
                        "shot_title": "深圳CBD航拍",
                        "scene_group": "深圳CBD",
                        "action_description": "深圳CBD城市天际线航拍",
                    },
                    {
                        "shot_id": "shot_002",
                        "shot_title": "端午粽子礼盒特写",
                        "scene_group": "节日礼盒",
                        "action_description": "粽子礼盒静物摆放",
                    },
                ],
            )
            _write_json(
                project / "00_调研" / "精选参考帧" / "精选参考帧清单.json",
                {
                    "frames": [
                        {
                            "frame_id": "frame_cbd",
                            "selected_frame_path": str(project / "00_调研" / "精选参考帧" / "帧图片" / "精选帧_0001.png"),
                            "commercial_direction": "深圳CBD",
                            "allowed_usage": ["composition_reference"],
                        }
                    ]
                },
            )
            _write_json(
                project / "00_调研" / "精选参考帧" / "参考帧分析.json",
                {"frames": [{"frame_id": "frame_cbd", "scene": "深圳CBD城市天际线", "reference_strength": 9, "image2_usage_weight": 0.9}]},
            )

            result = build_reference_frame_binding_plan(project)
            storyboard = json.loads((project / "01_分镜" / "分镜总表.json").read_text(encoding="utf-8"))
            plan = json.loads(Path(result["system_output_binding_plan"]).read_text(encoding="utf-8"))

            self.assertEqual(storyboard[0]["reference_frame_ids"], ["frame_cbd"])
            self.assertEqual(storyboard[1]["reference_frame_ids"], [])
            self.assertEqual(plan["items"][1]["reference_frame_ids"], [])
            self.assertEqual(plan["reuse_counts"], {"frame_cbd": 1})


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
