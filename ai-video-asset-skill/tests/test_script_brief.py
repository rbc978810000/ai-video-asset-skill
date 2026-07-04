from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ai_video_asset_skill.config import build_style_bible, derive_shot_count_from_duration, merge_input
from ai_video_asset_skill.main_orchestrator import _build_script_brief


class ScriptBriefTests(unittest.TestCase):
    def test_duration_estimates_shot_count_when_total_shots_not_supplied(self) -> None:
        settings = merge_input({"user_input_duration_seconds": 30})

        self.assertEqual(derive_shot_count_from_duration(30), 12)
        self.assertEqual(settings["user_input_total_shots"], 12)

    def test_script_brief_defaults_to_silent_16x9_market_derived_direction(self) -> None:
        settings = merge_input(
            {
                "user_input_topic_title": "深圳城市 AI 视频素材",
                "user_input_industry_name": "城市宣传",
                "user_input_duration_seconds": 30,
            }
        )
        style_bible = build_style_bible(settings)
        brief = _build_script_brief(
            settings,
            style_bible,
            {
                "visual_demand_matrix": [{"direction_name": "深圳CBD天际线与城市航拍"}],
                "market_signal_map": [{"buyer_use_case": "城市宣传片"}],
            },
            "00_调研/市场反挖/市场反挖摘要.json",
        )

        self.assertEqual(brief["aspect_ratio"], "16:9")
        self.assertFalse(brief["needs_voiceover"])
        self.assertFalse(brief["needs_subtitles"])
        self.assertEqual(brief["shot_count"], 12)
        self.assertIn("深圳CBD天际线与城市航拍", brief["commercial_direction_basis"])
        self.assertIn("城市宣传片", brief["target_buyer_groups"])


if __name__ == "__main__":
    unittest.main()
