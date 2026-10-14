import torch
import torch.nn as nn
import torch.nn.functional as F

N_FFT = 1280
HOP = 320
SAMPLE_RATE = 24000
CODES_PER_SECOND = SAMPLE_RATE // HOP  # 75

CODEBOOK_KEY = "feature_extractor.encodec.quantizer.vq.layers.0._codebook.embed"


class AdaLayerNorm(nn.Module):
    def __init__(self, num_embeddings: int, dim: int, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.dim = dim
        self.scale = nn.Embedding(num_embeddings, dim)
        self.shift = nn.Embedding(num_embeddings, dim)

    def forward(self, x, cond_id):
        scale = self.scale(cond_id)
        shift = self.shift(cond_id)
        x = F.layer_norm(x, (self.dim,), eps=self.eps)
        return x * scale + shift


class ConvNeXtBlock(nn.Module):
    def __init__(self, dim: int, inter_dim: int, num_bandwidths: int):
        super().__init__()
        self.dwconv = nn.Conv1d(dim, dim, kernel_size=7, padding=3, groups=dim)
        self.norm = AdaLayerNorm(num_bandwidths, dim, eps=1e-6)
        self.pwconv1 = nn.Linear(dim, inter_dim)
        self.pwconv2 = nn.Linear(inter_dim, dim)
        self.gamma = nn.Parameter(torch.ones(dim))

    def forward(self, x, cond_id):
        residual = x
        x = self.dwconv(x).transpose(1, 2)          # [B,T,C]
        x = self.norm(x, cond_id)
        x = self.pwconv2(F.gelu(self.pwconv1(x)))
        x = (self.gamma * x).transpose(1, 2)         # [B,C,T]
        return residual + x


def _swish(x):
    return x * torch.sigmoid(x)


class ResnetBlock(nn.Module):
    def __init__(self, dim: int):
        super().__init__()
        self.norm1 = nn.GroupNorm(32, dim, eps=1e-6, affine=True)
        self.conv1 = nn.Conv1d(dim, dim, kernel_size=3, padding=1)
        self.norm2 = nn.GroupNorm(32, dim, eps=1e-6, affine=True)
        self.conv2 = nn.Conv1d(dim, dim, kernel_size=3, padding=1)

    def forward(self, x):
        h = self.conv1(_swish(self.norm1(x)))
        h = self.conv2(_swish(self.norm2(h)))
        return x + h


class AttnBlock(nn.Module):
    """Single-head full (non-causal) self-attention over time, channels as the head dim."""

    def __init__(self, dim: int):
        super().__init__()
        self.norm = nn.GroupNorm(32, dim, eps=1e-6, affine=True)
        self.q = nn.Conv1d(dim, dim, kernel_size=1)
        self.k = nn.Conv1d(dim, dim, kernel_size=1)
        self.v = nn.Conv1d(dim, dim, kernel_size=1)
        self.proj_out = nn.Conv1d(dim, dim, kernel_size=1)

    def forward(self, x):
        h = self.norm(x)
        q = self.q(h).transpose(1, 2)                # [B,T,C]
        k = self.k(h).transpose(1, 2)
        v = self.v(h).transpose(1, 2)
        a = F.scaled_dot_product_attention(q, k, v)   # scale = C ** -0.5
        return x + self.proj_out(a.transpose(1, 2))


class VocosBackbone(nn.Module):
    def __init__(self, in_dim=512, dim=768, inter_dim=2304, num_layers=12, num_bandwidths=4):
        super().__init__()
        self.embed = nn.Conv1d(in_dim, dim, kernel_size=7, padding=3)
        self.norm = AdaLayerNorm(num_bandwidths, dim, eps=1e-6)
        self.convnext = nn.ModuleList(
            [ConvNeXtBlock(dim, inter_dim, num_bandwidths) for _ in range(num_layers)]
        )
        self.final_layer_norm = nn.LayerNorm(dim, eps=1e-6)
        self.pos_net = nn.Sequential(
            ResnetBlock(dim),
            ResnetBlock(dim),
            AttnBlock(dim),
            ResnetBlock(dim),
            ResnetBlock(dim),
            nn.GroupNorm(32, dim, eps=1e-6, affine=True),
        )

    def forward(self, x, bandwidth_id):
        x = self.embed(x)                             # [B,768,T]
        x = self.pos_net(x)
        x = self.norm(x.transpose(1, 2), bandwidth_id).transpose(1, 2)
        for block in self.convnext:
            x = block(x, bandwidth_id)
        return self.final_layer_norm(x.transpose(1, 2))   # [B,T,768]


class ISTFT(nn.Module):
    """'same'-padding ISTFT (overlap-add + window-envelope normalisation)."""

    def __init__(self, n_fft=N_FFT, hop=HOP):
        super().__init__()
        self.n_fft, self.hop = n_fft, hop
        self.register_buffer("window", torch.hann_window(n_fft))   # overwritten by ckpt

    def forward(self, spec):                          # spec: complex [B, n_fft//2+1, T]
        T = spec.shape[-1]
        pad = (self.n_fft - self.hop) // 2
        frames = torch.fft.irfft(spec, self.n_fft, dim=1, norm="backward")
        frames = frames * self.window[None, :, None]
        out_len = (T - 1) * self.hop + self.n_fft
        y = F.fold(frames, output_size=(1, out_len), kernel_size=(1, self.n_fft),
                   stride=(1, self.hop))[:, 0, 0, pad:-pad]
        w2 = self.window.square().expand(1, T, -1).transpose(1, 2)
        env = F.fold(w2, output_size=(1, out_len), kernel_size=(1, self.n_fft),
                     stride=(1, self.hop)).squeeze()[pad:-pad]
        return y / env


class ISTFTHead(nn.Module):
    def __init__(self, dim=768, n_fft=N_FFT, hop=HOP):
        super().__init__()
        self.out = nn.Linear(dim, n_fft + 2)
        self.istft = ISTFT(n_fft, hop)

    def forward(self, x):                             # x: [B,T,768]
        x = self.out(x).transpose(1, 2)               # [B,1282,T]
        mag, phase = x.chunk(2, dim=1)
        mag = torch.exp(mag).clamp(max=1e2)
        spec = mag * (torch.cos(phase) + 1j * torch.sin(phase))
        return self.istft(spec)


class WavTokenizerDecoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.codebook = nn.Embedding(4096, 512)
        self.backbone = VocosBackbone()
        self.head = ISTFTHead()

    @torch.inference_mode()
    def forward(self, codes: torch.Tensor) -> torch.Tensor:
        """codes: LongTensor [B,T] with values 0..4095 -> float waveform [B, T*320] @ 24 kHz."""
        feats = self.codebook(codes).transpose(1, 2)              # [B,512,T]
        bw = torch.zeros(1, dtype=torch.long, device=codes.device)  # bandwidth_id = 0
        return self.head(self.backbone(feats, bw))


def _extract(sd: dict) -> dict:
    """Keep only what the decoder needs, under this module's key names."""
    keep = {"codebook.weight": sd[CODEBOOK_KEY]}
    for k, v in sd.items():
        if k.startswith("backbone.") or k.startswith("head."):
            keep[k] = v
    return keep


def _load_sd(path: str) -> dict:
    """Read any of the supported files and return keys in this module's naming:
       1) original WavTokenizer .ckpt  (feature_extractor.encodec...embed + backbone.* + head.*)
       2) slim file from export_slim()
       3) OuteAI's decoder/decoder_model.pt  ({'model_state_dict', 'codebook_weights'})
    """
    try:
        obj = torch.load(path, map_location="cpu", weights_only=True)
    except Exception:                       # Lightning ckpts hold non-tensor objects
        obj = torch.load(path, map_location="cpu", weights_only=False)
    if isinstance(obj, dict) and "model_state_dict" in obj:          # OuteAI format
        sd = dict(obj["model_state_dict"])
        cb = sd.pop("codebook_weights", None)
        if cb is None:
            cb = obj["codebook_weights"]
        sd["codebook.weight"] = cb
        return {k: v for k, v in sd.items() if k == "codebook.weight" or k.startswith(("backbone.", "head."))}
    sd = obj.get("state_dict", obj) if isinstance(obj, dict) else obj
    if CODEBOOK_KEY in sd:
        sd = _extract(sd)
    return sd


def load_decoder(path: str, device: str = "cpu") -> WavTokenizerDecoder:
    model = WavTokenizerDecoder()
    model.load_state_dict(_load_sd(path), strict=True)   # any name/shape mismatch raises
    return model.to(device).eval()


def export_slim(ckpt_path: str, out_path: str):
    """Write only the decoder tensors, so the big ckpt is no longer needed."""
    torch.save(_load_sd(ckpt_path), out_path)


def compare_decoders(path_a: str, path_b: str):
    """Are two decoder files the same weights? Prints the max abs difference per part."""
    a, b = _load_sd(path_a), _load_sd(path_b)
    print("keys only in A:", sorted(set(a) - set(b))[:5], "| only in B:", sorted(set(b) - set(a))[:5])
    parts = {}
    for k in sorted(set(a) & set(b)):
        part = "codebook" if k.startswith("codebook") else k.split(".")[0] + "." + k.split(".")[1]
        d = (a[k].float() - b[k].float()).abs().max().item() if a[k].shape == b[k].shape else float("inf")
        parts[part] = max(parts.get(part, 0.0), d)
    for part, d in parts.items():
        print(f"  {part:<22} max abs diff {d:.3g}")
    same = all(d == 0.0 for d in parts.values())
    print("IDENTICAL weights" if same else "DIFFERENT weights")
    return same