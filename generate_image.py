"""Generate images from a text prompt using Google GenAI."""

import argparse
import base64
import json
import logging
import mimetypes
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

DEFAULT_MODEL = os.getenv(
    "GENAI_IMAGE_MODEL",
    "gemini-2.0-flash-preview-image-generation",
)
DEFAULT_OUTPUT_DIR = Path("generated_images")
LOGGER = logging.getLogger("generate_image")


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Generate an image from a prompt with Google GenAI."
    )
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt", help="Prompt text to send to the model.")
    prompt_group.add_argument(
        "--prompt-file",
        type=Path,
        help="Path to a UTF-8 text file containing the prompt.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where generated files should be written.",
    )
    parser.add_argument(
        "--filename",
        help="Optional output file stem. Defaults to a slug plus timestamp.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Google GenAI model id to use for image generation.",
    )
    parser.add_argument(
        "--api-key-env",
        default="GOOGLE_API_KEY",
        help="Primary environment variable to read for the API key.",
    )
    parser.add_argument(
        "--max-images",
        type=int,
        default=1,
        help="Maximum number of images to save from the response.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate arguments and show the planned output without calling the API.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    return parser


def configure_logging(level: str) -> None:
    """Configure logging for the CLI."""
    logging.basicConfig(level=getattr(logging, level), format="%(levelname)s: %(message)s")


def slugify(value: str) -> str:
    """Convert text into a safe ASCII file stem."""
    ascii_value = value.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug or "image"


def load_prompt(prompt: Optional[str], prompt_file: Optional[Path]) -> str:
    """Load the prompt from a CLI argument or a file."""
    if prompt:
        value = prompt.strip()
    elif prompt_file:
        value = prompt_file.read_text(encoding="utf-8").strip()
    else:
        raise ValueError("Provide either --prompt or --prompt-file.")

    if not value:
        raise ValueError("Prompt cannot be empty.")

    return value


def resolve_api_key(api_key_env: str) -> str:
    """Resolve the API key from the requested environment variable."""
    fallback_keys = [api_key_env]
    if api_key_env != "GEMINI_API_KEY":
        fallback_keys.append("GEMINI_API_KEY")
    if api_key_env != "GOOGLE_API_KEY":
        fallback_keys.append("GOOGLE_API_KEY")

    for key_name in fallback_keys:
        value = os.getenv(key_name)
        if value:
            return value

    raise RuntimeError(
        f"Missing API key. Set {api_key_env}, GOOGLE_API_KEY, or GEMINI_API_KEY."
    )


def build_output_stem(filename: Optional[str], prompt: str) -> str:
    """Build a stable file stem for output artifacts."""
    if filename:
        return slugify(filename)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{slugify(prompt)[:48]}-{timestamp}"


def extension_for_mime(mime_type: str) -> str:
    """Resolve a file extension from a MIME type."""
    custom_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }
    return custom_map.get(mime_type, mimetypes.guess_extension(mime_type) or ".bin")


def load_genai_client(api_key_env: str):
    """Import and initialize the Google GenAI client on demand."""
    api_key = resolve_api_key(api_key_env)

    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai is not installed. Run: pip install -r requirements.txt"
        ) from exc

    return genai.Client(api_key=api_key), types


def request_generation(prompt: str, model: str, api_key_env: str):
    """Send the prompt to Google GenAI and return the raw response."""
    client, types = load_genai_client(api_key_env)
    config = types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"])
    return client.models.generate_content(
        model=model,
        contents=prompt,
        config=config,
    )


def extract_inline_images(response) -> List[Tuple[bytes, str]]:
    """Extract inline image payloads from the response."""
    images: List[Tuple[bytes, str]] = []
    candidates = getattr(response, "candidates", None) or []

    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline_data = getattr(part, "inline_data", None)
            raw_data = getattr(inline_data, "data", None)
            mime_type = getattr(inline_data, "mime_type", None)
            if not raw_data or not mime_type:
                continue

            if isinstance(raw_data, str):
                image_bytes = base64.b64decode(raw_data)
            else:
                image_bytes = raw_data

            if mime_type.startswith("image/"):
                images.append((image_bytes, mime_type))

    return images


def extract_text_fragments(response) -> List[str]:
    """Collect any text fragments that accompanied the generated images."""
    fragments: List[str] = []
    candidates = getattr(response, "candidates", None) or []

    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            text = getattr(part, "text", None)
            if text:
                fragments.append(text)

    response_text = getattr(response, "text", None)
    if response_text and response_text not in fragments:
        fragments.append(response_text)

    return fragments


def write_outputs(
    output_dir: Path,
    stem: str,
    images: Sequence[Tuple[bytes, str]],
    metadata: Dict,
) -> Tuple[List[Path], Path]:
    """Persist generated image files and a metadata manifest."""
    output_dir.mkdir(parents=True, exist_ok=True)

    written_files: List[Path] = []
    for index, (image_bytes, mime_type) in enumerate(images, start=1):
        suffix = "" if len(images) == 1 else f"-{index}"
        extension = extension_for_mime(mime_type)
        image_path = output_dir / f"{stem}{suffix}{extension}"
        image_path.write_bytes(image_bytes)
        written_files.append(image_path)

    metadata_path = output_dir / f"{stem}.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return written_files, metadata_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the image generation CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)

    try:
        if args.max_images < 1:
            raise ValueError("--max-images must be at least 1.")

        prompt = load_prompt(args.prompt, args.prompt_file)
        stem = build_output_stem(args.filename, prompt)

        if args.dry_run:
            print(f"Prompt length: {len(prompt)} characters")
            print(f"Model: {args.model}")
            print(f"Output directory: {args.output_dir}")
            print(f"Output stem: {stem}")
            return 0

        response = request_generation(prompt, args.model, args.api_key_env)
        images = extract_inline_images(response)[: args.max_images]
        if not images:
            raise RuntimeError("The model response did not include any image data.")

        text_fragments = extract_text_fragments(response)
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "model": args.model,
            "prompt": prompt,
            "image_count": len(images),
            "text_fragments": text_fragments,
        }

        written_files, metadata_path = write_outputs(args.output_dir, stem, images, metadata)

        print(f"Saved {len(written_files)} image(s):")
        for image_path in written_files:
            print(image_path)
        print(f"Metadata: {metadata_path}")
        return 0
    except Exception as exc:
        LOGGER.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
