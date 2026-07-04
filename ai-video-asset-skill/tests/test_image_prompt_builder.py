from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ai_video_asset_skill.config import build_style_bible, merge_input
from ai_video_asset_skill.image_prompt_builder import build_image_prompt


class ImagePromptBuilderTests(unittest.TestCase):
    def test_lab_topic_prompt_is_compact_and_does_not_leak_market_evidence(self) -> None:
        settings = merge_input(
            {
                "user_input_topic_title": "新材料科研团队实验室研发团队大学科研人员AI视频素材",
                "user_input_industry_name": "新材料科研与高校实验室",
                "user_input_visual_style": "真实摄影质感，现代高校与企业联合实验室，新材料研发场景，干净明亮",
                "user_input_people_region_priority": "中国科研人员、中国高校实验室团队、中国新材料企业研发人员",
            }
        )
        style_bible = build_style_bible(settings)
        shot = {
            "shot_id": "shot_001",
            "subject_main": "实验室研发团队 科研",
            "subject_secondary": ["实验室研发团队", "科研", "科研人员", "研究"],
            "action_description": "实验室研发团队 科研呈现实验室研发团队 科研，突出主题识别和商业素材价值",
            "scene_context": "现代新材料实验室，科研人员围绕材料样品和仪器协作",
            "shot_size": "全景",
            "camera_angle": "宽幅建立镜头机位",
            "camera_movement": "缓慢推进的运镜感",
            "composition_notes": "主体位于画面视觉重心，前景、中景、背景层次明确",
            "visual_style": settings["user_input_visual_style"],
            "lighting_style": style_bible["lighting_style"],
            "mood_tone": "高级、专业、干净、电影感",
            "color_palette": ", ".join(style_bible["color_palette"]),
            "copy_space": "画面完整可直接作为素材使用",
            "direct_use_composition": "画面完整可直接作为素材使用",
            "video_motion_intent": "科研人员自然观察、确认或讨论",
            "detailed_script": "来自光厂作品证据：35522250, 28215726。市场用途：实验室研发团队 科研。",
            "negative_constraints": list(style_bible["negative_constraints"]),
            "image_output_dir": "../03_图片/镜头_001",
        }

        prompt_data = build_image_prompt(shot, style_bible, "16:9")
        prompt = prompt_data["prompt"]

        self.assertLess(len(prompt), 900)
        self.assertNotIn("来自光厂作品证据", prompt)
        self.assertNotIn("市场用途", prompt)
        self.assertNotIn("统一风格锁定", prompt)
        self.assertNotIn("详细画面脚本", prompt)
        self.assertNotIn("机械臂", prompt)
        self.assertNotIn("AGV", prompt)
        self.assertIn("真实商业素材画面", prompt)
        self.assertEqual(prompt_data["prompt_version"], "compact_commercial_still_v3")
        self.assertIn("来自光厂作品证据", prompt_data["prompt_supporting_metadata"]["detailed_script"])

    def test_lab_style_bible_does_not_keep_smart_factory_equipment(self) -> None:
        settings = merge_input(
            {
                "user_input_topic_title": "新材料科研团队实验室研发团队大学科研人员AI视频素材",
                "user_input_industry_name": "新材料科研与高校实验室",
                "user_input_visual_style": "真实摄影质感，现代高校与企业联合实验室，新材料研发场景，干净明亮",
            }
        )

        style_bible = build_style_bible(settings)
        joined = " ".join(
            str(style_bible.get(key, ""))
            for key in ["factory_environment", "environment_style", "equipment_style"]
        )

        self.assertEqual(style_bible["style_id"], "research_lab_premium_001")
        self.assertIn("实验室", joined)
        self.assertIn("显微镜", joined)
        self.assertNotIn("机械臂", joined)
        self.assertNotIn("AGV", joined)
        self.assertNotIn("自动化产线", joined)

    def test_prompt_strips_production_labels_from_visible_subject(self) -> None:
        settings = merge_input(
            {
                "user_input_topic_title": "商务人士签约成功合作握手AI视频素材",
                "user_input_industry_name": "商务服务",
                "user_input_visual_style": "高端真实商务摄影风，现代中国企业会议室与写字楼场景",
            }
        )
        style_bible = build_style_bible(settings)
        shot = {
            "shot_id": "shot_001",
            "subject_main": "商务人士签约成功合作握手AI视频素材 商务合作",
            "subject_secondary": ["商务人士签约成功合作握手AI视频素材", "商务合作", "商务签约"],
            "action_description": "商务人士签约成功合作握手AI视频素材 商务合作呈现商务人士签约成功合作握手AI视频素材 商务合作，突出主题识别",
            "scene_context": "商务人士签约成功合作握手AI视频素材商业化素材方向相关场景",
            "shot_size": "中景",
            "camera_angle": "平视机位",
            "camera_movement": "稳定横移跟拍的运镜感",
            "composition_notes": "主体位于画面视觉重心，前中后景层次明确",
            "visual_style": settings["user_input_visual_style"],
            "lighting_style": style_bible["lighting_style"],
            "mood_tone": "高级、专业、干净",
            "color_palette": ", ".join(style_bible["color_palette"]),
            "copy_space": "主体居中稳定",
            "negative_constraints": list(style_bible["negative_constraints"]),
            "image_output_dir": "../03_图片/镜头_001",
        }

        prompt = build_image_prompt(shot, style_bible, "16:9")["prompt"]

        self.assertNotIn("AI视频素材", prompt)
        self.assertNotIn("商业化素材方向", prompt)
        self.assertIn("商务人士签约成功合作握手 商务合作", prompt)


if __name__ == "__main__":
    unittest.main()
