# The beta version is being developed using PyTorch.
# In future versions, I'll replace PyTorch with lightweight libraries
# to perform the required operations and reduce the final application size.
import logging

import torch
from safetensors import safe_open

from backend.models.tts.outeTTSProcessing import *

logger = logging.getLogger(__name__)

class OutettsAttention(torch.nn.Module):
    """OuteTTS attention module."""

    def __init__(self, config: dict, layer_no: int, safetensor_files: list):
        super().__init__()

        self.d_model = config["hidden_size"]
        self.num_attn_heads = config["num_attention_heads"]
        self.num_kv_heads = config["num_key_value_heads"]
        self.attn_dim = 64
        self.max_seq_len = 512
        self.files = safetensor_files
        self.init_rope(config)

        self.q_proj = torch.nn.Linear(
            in_features=self.d_model, out_features=self.d_model
        )
        self.k_proj = torch.nn.Linear(
            in_features=self.d_model,
            out_features=self.attn_dim * self.num_kv_heads,
        )
        self.v_proj = torch.nn.Linear(
            in_features=self.d_model,
            out_features=self.attn_dim * self.num_kv_heads,
        )
        self.o_proj = torch.nn.Linear(self.d_model, self.d_model, bias=False)

        self.register_buffer(
            "mask",
            torch.triu(
                torch.ones(self.max_seq_len, self.max_seq_len),
                diagonal=1,
            ).bool(),
        )

        # weight
        self.q_proj.weight.data.copy_(
            self.get_tensor(f"model.layers.{layer_no}.self_attn.q_proj.weight")
        )
        self.k_proj.weight.data.copy_(
            self.get_tensor(f"model.layers.{layer_no}.self_attn.k_proj.weight")
        )
        self.v_proj.weight.data.copy_(
            self.get_tensor(f"model.layers.{layer_no}.self_attn.v_proj.weight")
        )
        self.o_proj.weight.data.copy_(
            self.get_tensor(f"model.layers.{layer_no}.self_attn.o_proj.weight")
        )

        # bias
        self.q_proj.bias.data.copy_(
            self.get_tensor(f"model.layers.{layer_no}.self_attn.q_proj.bias")
        )
        self.k_proj.bias.data.copy_(
            self.get_tensor(f"model.layers.{layer_no}.self_attn.k_proj.bias")
        )
        self.v_proj.bias.data.copy_(
            self.get_tensor(f"model.layers.{layer_no}.self_attn.v_proj.bias")
        )

    @torch.no_grad()
    def forward(self, x, past_kv=None):
        # In very first loop the shape will be [1, S, D] -> Then input always [1, 1, D]

        B, S, _ = x.shape

        q = (
            self.q_proj(x)
            .view(B, S, self.num_attn_heads, self.attn_dim)
            .transpose(1, 2)
        )
        k = self.k_proj(x).view(B, S, self.num_kv_heads, self.attn_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, S, self.num_kv_heads, self.attn_dim).transpose(1, 2)

        past_len = 0 if past_kv is None else past_kv[0].shape[2]
        position_ids = (
            torch.arange(
                past_len,
                past_len + S,
                device=x.device,
            )
            .unsqueeze(0)
            .expand(B, -1)
        )
        q, k = self.apply_rope(q, k, position_ids)

        if past_kv:
            past_k, past_v = past_kv

            k = torch.cat([past_k, k], dim=2)
            v = torch.cat([past_v, v], dim=2)

        present_kv = (k, v)

        num_groups = self.num_attn_heads // self.num_kv_heads

        k = k.repeat_interleave(num_groups, dim=1)
        v = v.repeat_interleave(num_groups, dim=1)

        scores = q @ k.transpose(-2, -1) * (self.attn_dim**-0.5)

        if S > 1:
            causal = torch.triu(
                torch.ones(S, S, dtype=torch.bool, device=x.device), diagonal=1
            )
            scores = scores.masked_fill(causal, float("-inf"))

        wei = torch.softmax(scores, dim=-1)

        v_rep = wei @ v
        out = v_rep.transpose(1, 2).contiguous()
        out = out.view(B, S, self.d_model)
        out = self.o_proj(out)

        return out, present_kv

    def get_tensor(self, name):

        for file in self.files:
            if name in file.keys():
                return file.get_tensor(name)

    def init_rope(self, config: dict):
        # Qwen2 rotary embedding configuration
        theta = config["rope_theta"]
        dim = self.attn_dim

        # Calculate inverse frequencies in float32
        inv_freq = 1.0 / (theta ** (torch.arange(0, dim, 2, dtype=torch.float32) / dim))

        self.register_buffer(
            "inv_freq",
            inv_freq,
            persistent=False,
        )

    def rotate_half(self, x):
        # Original Qwen2/Hugging Face rotation convention
        x1 = x[..., : x.shape[-1] // 2]
        x2 = x[..., x.shape[-1] // 2 :]

        return torch.cat((-x2, x1), dim=-1)

    def apply_rope(self, q, k, position_ids):
        # q: [B, num_attention_heads, S, head_dim]
        # k: [B, num_kv_heads, S, head_dim]
        # position_ids: [B, S]

        inv_freq = self.inv_freq.float().to(q.device)

        inv_freq = inv_freq[None, :, None].expand(position_ids.shape[0], -1, -1)

        position_ids = position_ids[:, None, :].float()

        with torch.autocast(
            device_type=q.device.type,
            enabled=False,
        ):
            freqs = (inv_freq @ position_ids).transpose(1, 2)

            # Duplicate frequencies across both halves of head_dim
            emb = torch.cat((freqs, freqs), dim=-1)

            cos = emb.cos()
            sin = emb.sin()

        # Match the input tensor dtype
        cos = cos.to(dtype=q.dtype).unsqueeze(1)
        sin = sin.to(dtype=q.dtype).unsqueeze(1)

        q = q * cos + self.rotate_half(q) * sin
        k = k * cos + self.rotate_half(k) * sin

        return q, k


class OutettsFeedForwardNetwork(torch.nn.Module):
    """OuteTTS feed-forward network module."""

    def __init__(self, config: dict, layer_no: int, safetensor_files: list):
        super().__init__()

        self.files = safetensor_files

        self.up_proj = torch.nn.Linear(
            in_features=config["hidden_size"],
            out_features=config["intermediate_size"],
            bias=False,
        )
        self.gate_proj = torch.nn.Linear(
            in_features=config["hidden_size"],
            out_features=config["intermediate_size"],
            bias=False,
        )
        self.down_proj = torch.nn.Linear(
            in_features=config["intermediate_size"],
            out_features=config["hidden_size"],
            bias=False,
        )

        # weight
        self.up_proj.weight.data.copy_(
            self.get_tensor(f"model.layers.{layer_no}.mlp.up_proj.weight")
        )
        self.gate_proj.weight.data.copy_(
            self.get_tensor(f"model.layers.{layer_no}.mlp.gate_proj.weight")
        )
        self.down_proj.weight.data.copy_(
            self.get_tensor(f"model.layers.{layer_no}.mlp.down_proj.weight")
        )

    @torch.no_grad()
    def forward(self, x):

        out = torch.nn.functional.silu(self.gate_proj(x)) * self.up_proj(x)

        return self.down_proj(out)

    def get_tensor(self, name):

        for file in self.files:
            if name in file.keys():
                return file.get_tensor(name)


class OutettsDecoderLayer(torch.nn.Module):
    """Single OuteTTS decoder layer."""

    def __init__(self, config: dict, layer_no: int, safetensor_files: list):
        super().__init__()

        self.files = safetensor_files

        self.input_layernorm = torch.nn.RMSNorm(
            config["hidden_size"], eps=config["rms_norm_eps"]
        )
        self.self_attn = OutettsAttention(config, layer_no, safetensor_files)
        self.post_attention_layernorm = torch.nn.RMSNorm(
            config["hidden_size"], eps=config["rms_norm_eps"]
        )
        self.mlp = OutettsFeedForwardNetwork(config, layer_no, safetensor_files)

        # weight
        self.input_layernorm.weight.data.copy_(
            self.get_tensor(f"model.layers.{layer_no}.input_layernorm.weight")
        )
        self.post_attention_layernorm.weight.data.copy_(
            self.get_tensor(f"model.layers.{layer_no}.post_attention_layernorm.weight")
        )

    @torch.no_grad()
    def forward(self, x, past_kv=None):

        residual = x

        x, present_kv = self.self_attn(self.input_layernorm(x), past_kv)
        x = residual + x

        return x + self.mlp(self.post_attention_layernorm(x)), present_kv

    def get_tensor(self, name):

        for file in self.files:
            if name in file.keys():
                return file.get_tensor(name)


class Outetts(torch.nn.Module):
    """
    OuteTTS is a text-to-speech model capable of generating speech in four languages:
    English, Korean, Chinese, and Japanese.

    This 500-million-parameter model takes a text file containing a script written
    in one of its supported languages and generates speech in the selected speaker's voice.

    Parameters
    ----------
    tokenizer_path : str
        Path to the model's official tokenizer file.

    config : dict
        Model configuration loaded from the configuration JSON file.

    safetensor_files : list[str]
        List of paths to the model's weight files.

    NOTE The script language and the speaker's language must match.

    Returns
    -------
    list
        Generated speech codes.
    """

    def __init__(
        self,
        tokenizer_path: str,
        config: dict,
        safetensor_files: list[str]
    ):
        super().__init__()

        self.tok = OuteTokenizer(tokenizer_path)

        self.num_layers = config["num_hidden_layers"]
        self.stop_ids = config["eos_token_id"]
        self.vocab = config["vocab_size"]

        self.files = [
            safe_open(file, framework="pt", device="cpu") for file in safetensor_files
        ]

        self.kv_cache = [None] * self.num_layers

        self.embed_tokens = torch.nn.Embedding(
            num_embeddings=config["vocab_size"], embedding_dim=config["hidden_size"]
        )

        self.layers = torch.nn.ModuleList(
            [OutettsDecoderLayer(config, i, self.files) for i in range(self.num_layers)]
        )

        self.final_norm = torch.nn.RMSNorm(
            config["hidden_size"], eps=config["rms_norm_eps"]
        )

        # weight
        self.embed_tokens.weight.data.copy_(
            self.get_tensor("model.embed_tokens.weight")
        )
        self.final_norm.weight.data.copy_(self.get_tensor("model.norm.weight"))

    @torch.inference_mode()
    def forward(
        self,
        script_path: str,
        speaker_location: str = "",
        max_length: int = 4096,
        temperature: float = 0.1,
        repetition_penalty: float = 1.1,
        top_k: int = 50,
        top_p: float = 1.0,
        min_p: float = 0.0,
        seed: int = 0,
    ) -> list[int]:
        """
        Generate speech codes from a script using the selected speaker's voice.

        Parameters
        ----------
        script_path : str
            Path to the text file containing the script in a supported language.
        
        speaker_location : str, default=None
            Path to the speaker profile containing the voice characteristics to use
            for speech generation.

        max_length : int, default=4096
            Maximum number of tokens the model can generate.

        Returns
        -------
        list
            Generated speech tokens.
        """

        script_content = load_translation_file(script_path)

        if not script_content:
            raise ValueError(f"Invalid translation content received: {script_content}.")

        speaker = load_speaker(speaker_location) if os.path.exists(speaker_location) else None
        if not speaker:
            logger.info(f"Unable to load speaker. Starting with the default speaker.")

        prompt_ids = self.tok.encode_prompt(text=script_content, speaker=speaker)

        self.eval()
        self.clear_kv_cache()

        device = self.embed_tokens.weight.device
        gen = None
        if seed is not None:
            gen = torch.Generator(device="cpu").manual_seed(seed)

        seen = torch.zeros(self.vocab, dtype=torch.bool, device=device)
        seen[torch.tensor(prompt_ids, device=device)] = True
        step_ids = torch.tensor([prompt_ids], dtype=torch.long, device=device)
        new_tokens = []

        for _ in range(max_length):
            x = self.embed_tokens(step_ids)
            for i, layer in enumerate(self.layers):
                x, self.kv_cache[i] = layer(x, self.kv_cache[i])
            hidden = self.final_norm(x[:, -1, :])
            logits = (hidden @ self.embed_tokens.weight.T)[0]

            t = self._sample(
                logits.cpu(),
                seen.cpu(),
                temperature,
                repetition_penalty,
                top_k,
                top_p,
                min_p,
                gen,
            )

            if t == self.stop_ids:
                break
            new_tokens.append(t)
            seen[t] = True
            step_ids = torch.tensor([[t]], dtype=torch.long, device=device)

        return self.tok.extract_codes(new_tokens)

    def get_tensor(self, name):

        for file in self.files:
            if name in file.keys():
                return file.get_tensor(name)

    def clear_kv_cache(self):
        self.kv_cache = [None] * self.num_layers

    def _sample(
        self, logits, seen, temperature, repetition_penalty, top_k, top_p, min_p, gen
    ):
        logits = logits.float().clone()
        if repetition_penalty != 1.0:
            idx = seen.nonzero(as_tuple=True)[0]
            s = logits[idx]
            logits[idx] = torch.where(
                s < 0, s * repetition_penalty, s / repetition_penalty
            )
        logits = logits / temperature

        if top_k and top_k < logits.numel():
            kth = torch.topk(logits, top_k).values[-1]
            logits[logits < kth] = float("-inf")

        probs = torch.softmax(logits, dim=-1)

        if top_p < 1.0:
            sp, si = torch.sort(probs, descending=True)
            remove = (torch.cumsum(sp, dim=-1) - sp) > top_p
            probs[si[remove]] = 0.0

        if min_p > 0.0:
            probs[probs < min_p * probs.max()] = 0.0

        probs = probs / probs.sum()

        return int(torch.multinomial(probs, 1, generator=gen).item())
