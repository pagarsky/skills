"""Scene-detect frames in video.mp4. Save scene boundaries + one keyframe per scene.

Outputs:
    scenes.json             [{ index, start, end, mid, frame_path }]
    frames/scene_NNN.png    one keyframe per scene (from the midpoint)
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from scenedetect import open_video, SceneManager, ContentDetector
from scenedetect.scene_manager import save_images


def detect(video_path: Path, threshold: float, min_scene_sec: float) -> list[tuple[float, float]]:
    video = open_video(str(video_path))
    fps = video.frame_rate
    sm = SceneManager()
    sm.add_detector(ContentDetector(
        threshold=threshold,
        min_scene_len=int(min_scene_sec * fps),
    ))
    sm.detect_scenes(video=video, show_progress=False)
    scenes = sm.get_scene_list()
    return [(s[0].get_seconds(), s[1].get_seconds()) for s in scenes], fps, video


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("--out-dir", default=None)
    p.add_argument("--threshold", type=float, default=27.0,
                   help="ContentDetector threshold (lower = more sensitive)")
    p.add_argument("--min-scene-sec", type=float, default=4.0)
    p.add_argument("--width", type=int, default=960,
                   help="resize keyframes to this width")
    args = p.parse_args()

    video_path = Path(args.video).resolve()
    out_dir = Path(args.out_dir) if args.out_dir else video_path.parent
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    for old in frames_dir.glob("*.png"):
        old.unlink()

    t0 = time.time()
    scenes, fps, video = detect(video_path, args.threshold, args.min_scene_sec)
    detect_sec = time.time() - t0

    if not scenes:
        # If nothing detected (very static talking-head section), at least anchor 1 frame
        # at t=0 so the guide still has something visual.
        from scenedetect.frame_timecode import FrameTimecode
        scenes = [(0.0, video.duration.get_seconds())]

    # save_images wants the SceneManager's scene_list which uses FrameTimecode pairs.
    # We rebuild from seconds.
    from scenedetect.frame_timecode import FrameTimecode
    scene_list = []
    for s, e in scenes:
        scene_list.append(
            (FrameTimecode(s, fps=fps), FrameTimecode(e, fps=fps))
        )

    t1 = time.time()
    image_filenames = save_images(
        scene_list=scene_list,
        video=video,
        num_images=1,            # midpoint
        frame_margin=1,
        image_extension="png",
        encoder_param=95,
        image_name_template="scene_$SCENE_NUMBER",
        output_dir=str(frames_dir),
        width=args.width,
        show_progress=False,
    )
    save_sec = time.time() - t1

    records = []
    for i, ((start, end), files) in enumerate(zip(scenes, image_filenames.values()), 1):
        # files is a list (one per num_images) of basenames relative to output_dir
        frame = files[0] if files else None
        records.append({
            "index": i,
            "start": round(start, 3),
            "end": round(end, 3),
            "mid": round((start + end) / 2, 3),
            "duration": round(end - start, 3),
            "frame_path": f"frames/{frame}" if frame else None,
        })

    timings = {
        "detect_sec": round(detect_sec, 2),
        "save_sec": round(save_sec, 2),
        "n_scenes": len(records),
        "fps": fps,
        "threshold": args.threshold,
        "min_scene_sec": args.min_scene_sec,
        "scenes": records,
    }
    (out_dir / "scenes.json").write_text(json.dumps(timings, indent=2))
    print(json.dumps({k: v for k, v in timings.items() if k != "scenes"}, indent=2))


if __name__ == "__main__":
    main()
