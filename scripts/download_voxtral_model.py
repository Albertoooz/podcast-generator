#!/usr/bin/env python3
"""Download mistralai/Voxtral-4B-TTS-2603 from Hugging Face (requires HF_TOKEN if gated)."""

from __future__ import annotations

import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download Voxtral 4B TTS weights via huggingface_hub snapshot_download.",
    )
    parser.add_argument(
        "--local-dir",
        type=str,
        default="",
        help="Optional directory to store files. If omitted, uses the Hugging Face cache only.",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default="mistralai/Voxtral-4B-TTS-2603",
        help="Model repo id on Hugging Face.",
    )
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        print(
            "Error: set HF_TOKEN (or HUGGING_FACE_HUB_TOKEN) with read access to the model.",
            file=sys.stderr,
        )
        print(
            "Accept the model license on Hugging Face, then create a token at "
            "https://huggingface.co/settings/tokens",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("Install huggingface_hub: uv sync --group dev", file=sys.stderr)
        raise SystemExit(1) from None

    kwargs: dict = {"repo_id": args.repo, "token": token}
    if args.local_dir:
        kwargs["local_dir"] = args.local_dir

    path = snapshot_download(**kwargs)
    print(f"OK: snapshot at {path}")


if __name__ == "__main__":
    main()
