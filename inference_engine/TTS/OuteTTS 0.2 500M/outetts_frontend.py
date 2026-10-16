import json
import re
import wave

import numpy as np
import torch
from tokenizers import Tokenizer

try:
    import inflect

    _LEC = inflect.engine()
except ImportError:
    _LEC = None


# Text normalisation (same steps as the official PromptProcessor.process_text)

_ONES = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
_TENS = [
    "",
    "",
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
]
_SCALES = [
    (10**12, "trillion"),
    (10**9, "billion"),
    (10**6, "million"),
    (10**3, "thousand"),
]


def _int_to_words(n: int) -> str:
    """British-style 'and' like inflect: 204 -> 'two hundred and four'."""
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("" if n % 10 == 0 else "-" + _ONES[n % 10])
    if n < 1000:
        rest = n % 100
        return (
            _ONES[n // 100]
            + " hundred"
            + ("" if rest == 0 else " and " + _int_to_words(rest))
        )
    for value, name in _SCALES:
        if n >= value:
            rest = n % value
            head = _int_to_words(n // value) + " " + name
            if rest == 0:
                return head
            return head + (" and " if rest < 100 else ", ") + _int_to_words(rest)
    return str(n)


def number_to_words(num_str: str) -> str:
    if _LEC is not None:
        return _LEC.number_to_words(num_str)
    if "." in num_str:
        whole, frac = num_str.split(".", 1)
        return (
            _int_to_words(int(whole))
            + " point "
            + " ".join(_ONES[int(d)] for d in frac)
        )
    return _int_to_words(int(num_str))


def process_text(text: str) -> list[str]:
    text = re.sub(r"\d+(\.\d+)?", lambda m: number_to_words(m.group()), text.lower())
    text = re.sub(r"[-_/,\.\\]", " ", text)
    text = re.sub(r"[^a-z\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.split()


# Prompt (identical layout to the official get_completion_prompt)


def load_speaker(path: str) -> dict:
    """Speaker profile JSON: {"text": str, "words": [{"word","duration","codes"}], "language": "en"}"""
    with open(path, "r", encoding="utf-8") as f:
        sp = json.load(f)
    n_text = len(process_text(sp["text"]))
    if n_text != len(sp["words"]):
        print(
            f"warning: speaker text has {n_text} words but profile has {len(sp['words'])} entries"
        )
    return sp


def _audio_prompt(words: list) -> str:
    parts = []
    for w in words:
        codes = "".join(f"<|{c}|>" for c in w["codes"])
        parts.append(
            f'{w["word"]}<|t_{w["duration"]:.2f}|><|code_start|>{codes}<|code_end|>'
        )
    return "\n".join(parts)  # no trailing newline, exactly like the original


def build_prompt(text: str, speaker: dict | None = None) -> str:
    words = process_text(text)
    if speaker is not None:
        words = process_text(speaker["text"]) + words
    if not words:
        raise ValueError("Nothing left to speak after text normalisation.")
    prompt = (
        "<|im_start|>\n<|text_start|>"
        + "<|text_sep|>".join(words)
        + "<|text_end|>\n<|audio_start|>\n"
    )
    if speaker is not None:
        prompt += _audio_prompt(speaker["words"])
    return prompt


class OuteTokenizer:
    def __init__(self, tokenizer_json_path: str):
        self.tok = Tokenizer.from_file(tokenizer_json_path)
        pat = re.compile(r"^<\|(\d+)\|>$")
        self.code_of_id = {}
        for token, idx in self.tok.get_vocab().items():
            m = pat.match(token)
            if m and int(m.group(1)) < 4096:
                self.code_of_id[idx] = int(m.group(1))

    def encode_prompt(self, text: str, speaker: dict | None = None) -> list[int]:
        enc = self.tok.encode(build_prompt(text, speaker), add_special_tokens=False)
        # every <|...|> marker must be ONE token; a split marker means a missing vocab entry
        for t in enc.tokens:
            if ("<|" in t or "|>" in t) and not (
                t.startswith("<|") and t.endswith("|>")
            ):
                raise RuntimeError(f"Special token was split by the tokenizer: {t!r}")
        return enc.ids

    def extract_codes(self, generated_ids: list[int]) -> list[int]:
        return [self.code_of_id[i] for i in generated_ids if i in self.code_of_id]


# Sampling: the official package calls HF generate(do_sample=True, temperature=0.1,
#    repetition_penalty=1.1, max_length=4096) -> HF semantics:
#    * repetition penalty applies to EVERY token in the context (prompt + generated)
#    * max_length counts prompt + new tokens
#    * top_k / top_p / etc. come from the model's generation_config.json


def load_sampling_defaults(generation_config_path: str) -> dict:
    with open(generation_config_path, "r") as f:
        g = json.load(f)
    out = {k: g[k] for k in ("top_k", "top_p", "min_p") if k in g}
    out["eos_token_id"] = g.get("eos_token_id")
    return out


# WAV writer (stdlib only)


def save_wav(path: str, audio, sample_rate: int = 24000):
    a = (
        audio.detach().cpu().float().numpy()
        if torch.is_tensor(audio)
        else np.asarray(audio, dtype=np.float32)
    )
    a = np.clip(a.reshape(-1), -1.0, 1.0)
    pcm = (a * 32767.0).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())


def decode_codes_to_wav(codes: list[int], decoder) -> torch.Tensor:
    return decoder(
        torch.tensor([codes], dtype=torch.long)
    )  # [1, len(codes)*320] @ 24 kHz
