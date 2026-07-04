from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from ai_video_asset_skill.video_reference_assets import collect_video_reference_frames
from ai_video_asset_skill.video_scene_reference_assets import collect_scene_reference_frames


class VideoReferenceAssetsTests(unittest.TestCase):
    def test_collects_local_video_frames_and_reuses_existing_source(self) -> None:
        cv2 = __import__("cv2")
        np = __import__("numpy")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video_path = root / "sample.avi"
            writer = cv2.VideoWriter(
                str(video_path),
                cv2.VideoWriter_fourcc(*"MJPG"),
                5.0,
                (64, 36),
            )
            for index in range(10):
                frame = np.zeros((36, 64, 3), dtype=np.uint8)
                frame[:, :] = (20 + index * 18, 70, 130)
                frame[0:8, 0:16] = (255, 255, 255)
                writer.write(frame)
            writer.release()

            output_dir = root / "video_refs"
            result = collect_video_reference_frames(
                str(video_path),
                output_dir=output_dir,
                title="测试小样",
                frame_mode="sample",
                sample_every_seconds=0.2,
                max_frames=3,
                watermark_rect="0,0,16,8,64,36",
                watermark_backend="opencv",
            )

            self.assertTrue(result["system_output_success"])
            self.assertEqual(result["system_output_frame_count"], 3)
            manifest_path = Path(result["system_output_manifest"])
            aggregate_path = Path(result["system_output_aggregate_manifest"])
            self.assertTrue(manifest_path.exists())
            self.assertTrue(aggregate_path.exists())

            aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
            self.assertEqual(aggregate["frame_count"], 3)
            self.assertEqual(len(aggregate["assets"]), 3)
            for asset in aggregate["assets"]:
                self.assertTrue(Path(asset["resolved_path"]).exists())
                self.assertTrue(asset["watermark_removed"])
                self.assertEqual(asset["watermark_backend_used"], "opencv")

            reused = collect_video_reference_frames(
                str(video_path),
                output_dir=output_dir,
                title="测试小样",
                frame_mode="sample",
                sample_every_seconds=0.2,
                max_frames=3,
                watermark_rect="0,0,16,8,64,36",
                watermark_backend="opencv",
            )
            self.assertTrue(reused["system_output_reused_existing"])

    def test_collects_one_frame_per_transnet_scene(self) -> None:
        cv2 = __import__("cv2")
        np = __import__("numpy")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video_path = root / "sample.avi"
            writer = cv2.VideoWriter(
                str(video_path),
                cv2.VideoWriter_fourcc(*"MJPG"),
                5.0,
                (64, 36),
            )
            for index in range(20):
                frame = np.zeros((36, 64, 3), dtype=np.uint8)
                frame[:, :] = (30 + index * 8, 90, 150)
                writer.write(frame)
            writer.release()

            scenes = [
                {
                    "scene_id": "scene_0001",
                    "start_seconds": 0.0,
                    "end_seconds": 1.8,
                    "midpoint_seconds": 0.9,
                },
                {
                    "scene_id": "scene_0002",
                    "start_seconds": 2.0,
                    "end_seconds": 3.8,
                    "midpoint_seconds": 2.9,
                },
            ]

            with patch(
                "ai_video_asset_skill.video_scene_reference_assets._detect_transnet_scenes",
                return_value=scenes,
            ):
                result = collect_scene_reference_frames(
                    str(video_path),
                    output_dir=root / "scene_refs",
                    title="scene test",
                    watermark_backend="none",
                )

            self.assertTrue(result["system_output_success"])
            self.assertEqual(result["system_output_scene_count"], 2)
            self.assertEqual(result["system_output_frame_count"], 2)
            self.assertEqual(result["system_output_shot_count"], 2)

            frames = Path(result["system_output_frames_index"]).read_text(encoding="utf-8").strip().splitlines()
            shots = Path(result["system_output_shots_index"]).read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(frames), 2)
            self.assertEqual(len(shots), 2)
            first_frame = json.loads(frames[0])
            self.assertEqual(first_frame["shot_id"], "scene_0001")
            self.assertEqual(first_frame["scene_start_seconds"], 0.0)


if __name__ == "__main__":
    unittest.main()
