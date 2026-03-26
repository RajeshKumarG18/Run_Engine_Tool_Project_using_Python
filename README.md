# Run Engine Tool Project Using Python

This repository is a small Python demo project that simulates an "attention arbitrage" workflow. It is not wired to live social, payment, or scheduling APIs. The scripts model opportunity scoring, offer stacking, automated content generation, posting schedules, and order delivery with synthetic data.

## Architecture

- `run_engine.py` is the top-level orchestrator. It runs the core engine, prints the phase summaries, and executes one automation cycle demo.
- `attention_arbitrage_engine.py` contains the core simulation classes `AttentionArbitrage`, `MicroOfferStack`, `SilentDistribution`, and `FacelessRevenueEngine`.
- `automation_hub.py` simulates supporting automation work through `DataCollector`, `ContentGenerator`, `AutoPoster`, and `OfferDelivery`.
- `generate_image.py` is an optional CLI utility for generating images from a prompt via Google GenAI.
- `tests/` contains smoke tests for the engine math and image utility helpers.

## Requirements

- Python 3.10 or newer
- `google-genai` only if you want to use `generate_image.py`

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Run the main demo:

```bash
python3 run_engine.py
```

Run the engine module directly:

```bash
python3 attention_arbitrage_engine.py
```

Run the automation cycle directly:

```bash
python3 automation_hub.py
```

Validate the image generator without calling the API:

```bash
python3 generate_image.py --prompt "Futuristic running shoe on a studio pedestal" --dry-run
```

Generate an image with Google GenAI:

```bash
export GOOGLE_API_KEY="your-api-key"
python3 generate_image.py \
  --prompt "Minimal poster art of a runner in motion, warm sunrise palette" \
  --output-dir generated_images
```

## Testing

Syntax-check the scripts:

```bash
python3 -m py_compile run_engine.py automation_hub.py attention_arbitrage_engine.py generate_image.py
```

Run the smoke tests:

```bash
python3 -m unittest discover -s tests -v
```

## Notes

- The project is simulation-first. Outputs are illustrative, not live business forecasts.
- Results vary between runs because most of the automation logic uses randomized data.
- Generated image files are written to `generated_images/` by default and are ignored by Git.
