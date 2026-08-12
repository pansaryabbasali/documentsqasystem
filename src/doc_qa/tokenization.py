"""Token counting with the embedding model's own tokenizer.

Chunk budgets must be measured in the units the embedding model actually
consumes — character or word counts drift badly on technical text (part
numbers, units, torque values). Both M3 bake-off candidates
(all-MiniLM-L6-v2 and bge-small-en-v1.5) use near-identical BERT WordPiece
tokenizers, so chunking with the MiniLM tokenizer before the bake-off stays
valid whichever model wins.

The tokenizer file is fetched once from the Hugging Face Hub and cached
locally; the offline test suite injects a fake counter instead (no network).
"""

from __future__ import annotations

from collections.abc import Callable

DEFAULT_TOKENIZER_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_token_counter(model_name: str = DEFAULT_TOKENIZER_MODEL) -> Callable[[str], int]:
    """Return a callable that counts tokens the way ``model_name`` would."""
    from huggingface_hub import hf_hub_download  # lazy: keeps offline imports light
    from tokenizers import Tokenizer

    tokenizer = Tokenizer.from_file(hf_hub_download(model_name, "tokenizer.json"))
    # Shipped tokenizer.json may carry the model's padding/truncation config
    # (MiniLM's pads everything to 128 — every count came back 128 and the
    # splitter shredded pages into fragments). Counting must see raw lengths.
    tokenizer.no_padding()
    tokenizer.no_truncation()

    def count(text: str) -> int:
        return len(tokenizer.encode(text, add_special_tokens=False).ids)

    return count
