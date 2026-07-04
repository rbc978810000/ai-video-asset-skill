from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ai_video_asset_skill.config import build_style_bible, merge_input
from ai_video_asset_skill.storyboard_planner import generate_mock_storyboard


class StoryboardPlannerTests(unittest.TestCase):
    def test_market_summary_terms_do_not_leak_production_labels_into_subjects(self) -> None:
        settings = merge_input(
            {
                "user_input_topic_title": "商务人士签约成功合作握手AI视频素材",
                "user_input_industry_name": "商务服务",
                "user_input_total_shots": 1,
                "user_input_visual_style": "高端真实商务摄影风，现代中国企业会议室与写字楼场景",
            }
        )
        group_plan = [
            {
                "group_name": "商务人士签约成功合作握手AI视频素材商业化素材方向",
                "shot_count": 1,
                "representative_scenes": ["商务人士签约成功合作握手AI视频素材 商务合作"],
                "core_elements": ["商务人士签约成功合作握手AI视频素材", "商务合作"],
                "creative_angles": ["商务人士签约成功合作握手AI视频素材 商务合作"],
            }
        ]

        storyboard = generate_mock_storyboard(settings, build_style_bible(settings), group_plan)
        shot = storyboard[0]

        self.assertNotIn("AI视频素材", shot["subject_main"])
        self.assertNotIn("商业化素材方向", shot["scene_context"])
        self.assertIn("商务人士签约成功合作握手", shot["subject_main"])


if __name__ == "__main__":
    unittest.main()
