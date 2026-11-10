# The beta version is being developed using PyTorch.
# In future versions, I'll replace PyTorch with lightweight libraries
# to perform the required operations and reduce the final application size.

import torch
from safetensors import safe_open

from backend.models.stt.whisperProcessing import *


class WhisperEncoderAttention(torch.nn.Module):
    def __init__(self, config: dict, layer_no: int, safetensor_files: list):
        super().__init__()

        self.d_model = config["d_model"]
        self.num_head = config["encoder_attention_heads"]

        self.files = safetensor_files

        assert self.d_model % self.num_head == 0
        self.head_dim = self.d_model // self.num_head

        self.q_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.k_proj = torch.nn.Linear(self.d_model, self.d_model, bias=False)
        self.v_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.out_proj = torch.nn.Linear(self.d_model, self.d_model)

        # loading pretrained weights
        self.q_proj.weight.data.copy_(
            self.get_tensor(f"model.encoder.layers.{layer_no}.self_attn.q_proj.weight")
        )
        self.q_proj.bias.data.copy_(
            self.get_tensor(f"model.encoder.layers.{layer_no}.self_attn.q_proj.bias")
        )
        self.k_proj.weight.data.copy_(
            self.get_tensor(f"model.encoder.layers.{layer_no}.self_attn.k_proj.weight")
        )
        self.v_proj.weight.data.copy_(
            self.get_tensor(f"model.encoder.layers.{layer_no}.self_attn.v_proj.weight")
        )
        self.v_proj.bias.data.copy_(
            self.get_tensor(f"model.encoder.layers.{layer_no}.self_attn.v_proj.bias")
        )
        self.out_proj.weight.data.copy_(
            self.get_tensor(
                f"model.encoder.layers.{layer_no}.self_attn.out_proj.weight"
            )
        )
        self.out_proj.bias.data.copy_(
            self.get_tensor(f"model.encoder.layers.{layer_no}.self_attn.out_proj.bias")
        )

    @torch.no_grad()
    def forward(self, x):
        B, S, D = x.shape

        q = self.q_proj(x)
        k = self.k_proj(x)
        v = self.v_proj(x)

        q = q.view(B, S, self.num_head, self.head_dim).transpose(1, 2)
        k = k.view(B, S, self.num_head, self.head_dim).transpose(1, 2)
        v = v.view(B, S, self.num_head, self.head_dim).transpose(1, 2)

        attn_score = torch.einsum("bhqd, bhkd -> bhqk", q, k) * (self.head_dim**-0.5)
        wei = torch.nn.functional.softmax(attn_score, dim=-1)

        v_rep = wei @ v
        out = v_rep.transpose(1, 2).contiguous()
        out = out.view(B, S, self.d_model)

        return self.out_proj(out)

    def get_tensor(self, name):
        for f in self.files:
            if name in f.keys():
                return f.get_tensor(name)


class WhisperEncoderFeedForwardNeuralNetwork(torch.nn.Module):

    def __init__(self, config: dict, layer_no: int, safetensor_files: list):
        super().__init__()

        self.d_model = config["d_model"]
        self.d_ff = config["encoder_ffn_dim"]

        self.files = safetensor_files

        self.fc1 = torch.nn.Linear(in_features=self.d_model, out_features=self.d_ff)
        self.fc2 = torch.nn.Linear(in_features=self.d_ff, out_features=self.d_model)

        # loading pretrained weights
        self.fc1.weight.data.copy_(
            self.get_tensor(f"model.encoder.layers.{layer_no}.fc1.weight")
        )
        self.fc1.bias.data.copy_(
            self.get_tensor(f"model.encoder.layers.{layer_no}.fc1.bias")
        )
        self.fc2.weight.data.copy_(
            self.get_tensor(f"model.encoder.layers.{layer_no}.fc2.weight")
        )
        self.fc2.bias.data.copy_(
            self.get_tensor(f"model.encoder.layers.{layer_no}.fc2.bias")
        )

    @torch.no_grad()
    def forward(self, x):

        output = self.fc1(x)
        output = torch.nn.functional.gelu(output)

        return self.fc2(output)

    def get_tensor(self, name):
        for f in self.files:
            if name in f.keys():
                return f.get_tensor(name)


class WhisperEncoderLayer(torch.nn.Module):

    def __init__(self, config: dict, layer_no, safetensor_files: list):
        super().__init__()

        self.files = safetensor_files

        self.encoder_attn = WhisperEncoderAttention(config, layer_no, self.files)
        self.encoder_ffn = WhisperEncoderFeedForwardNeuralNetwork(
            config, layer_no, self.files
        )

        self.attn_layer_norm = torch.nn.LayerNorm(config["d_model"])
        self.attn_layer_norm.weight.data.copy_(
            self.get_tensor(
                f"model.encoder.layers.{layer_no}.self_attn_layer_norm.weight"
            )
        )
        self.attn_layer_norm.bias.data.copy_(
            self.get_tensor(
                f"model.encoder.layers.{layer_no}.self_attn_layer_norm.bias"
            )
        )

        self.final_layer_norm = torch.nn.LayerNorm(config["d_model"])
        self.final_layer_norm.weight.data.copy_(
            self.get_tensor(f"model.encoder.layers.{layer_no}.final_layer_norm.weight")
        )
        self.final_layer_norm.bias.data.copy_(
            self.get_tensor(f"model.encoder.layers.{layer_no}.final_layer_norm.bias")
        )

    @torch.no_grad()
    def forward(self, x):

        residual = x
        x = residual + self.encoder_attn(self.attn_layer_norm(x))

        residual = x
        x = residual + self.encoder_ffn(self.final_layer_norm(x))

        return x

    def get_tensor(self, name):
        for f in self.files:
            if name in f.keys():
                return f.get_tensor(name)


class WhisperEncoder(torch.nn.Module):

    def __init__(self, config: dict, safetensor_files: list):
        super().__init__()

        self.model_config = config
        self.files = safetensor_files

        self.conv1 = torch.nn.Conv1d(
            in_channels=self.model_config["num_mel_bins"],
            out_channels=self.model_config["d_model"],
            kernel_size=3,
            padding=1,
        )
        self.conv1.weight.data.copy_(self.get_tensor("model.encoder.conv1.weight"))
        self.conv1.bias.data.copy_(self.get_tensor("model.encoder.conv1.bias"))

        self.conv2 = torch.nn.Conv1d(
            in_channels=self.model_config["d_model"],
            out_channels=self.model_config["d_model"],
            kernel_size=3,
            stride=2,
            padding=1,
        )
        self.conv2.weight.data.copy_(self.get_tensor("model.encoder.conv2.weight"))
        self.conv2.bias.data.copy_(self.get_tensor("model.encoder.conv2.bias"))

        self.embed_positions = torch.nn.Embedding(
            num_embeddings=self.model_config["max_source_positions"],
            embedding_dim=self.model_config["d_model"],
        )
        self.embed_positions.weight.data.copy_(
            self.get_tensor("model.encoder.embed_positions.weight")
        )

        self.layers = torch.nn.ModuleList(
            [
                WhisperEncoderLayer(self.model_config, i, self.files)
                for i in range(self.model_config["encoder_layers"])
            ]
        )

        self.layer_norm = torch.nn.LayerNorm(config["d_model"])
        self.layer_norm.weight.data.copy_(
            self.get_tensor("model.encoder.layer_norm.weight")
        )
        self.layer_norm.bias.data.copy_(
            self.get_tensor("model.encoder.layer_norm.bias")
        )

    @torch.no_grad()
    def forward(self, x):

        x = torch.nn.functional.gelu(self.conv1(x))
        x = torch.nn.functional.gelu(self.conv2(x))

        x = x.transpose(-2, -1)

        positions = torch.arange(x.size(1), device=x.device)

        x = x + self.embed_positions(positions)

        for layer in self.layers:
            x = layer(x)

        return self.layer_norm(x)

    def get_tensor(self, name):

        for f in self.files:
            if name in f.keys():
                return f.get_tensor(name)


# Only One Seq will be came for process.


class WhisperDecoderMaskedAttention(torch.nn.Module):

    def __init__(self, config: dict, layer_no: int, safetensor_files: list):
        super().__init__()

        self.d_model = config["d_model"]
        self.num_head = config["decoder_attention_heads"]

        self.files = safetensor_files

        assert self.d_model % self.num_head == 0
        self.head_dim = self.d_model // self.num_head

        self.q_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.k_proj = torch.nn.Linear(self.d_model, self.d_model, bias=False)
        self.v_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.out_proj = torch.nn.Linear(self.d_model, self.d_model)

        self.register_buffer(
            "mask",
            torch.triu(
                torch.ones(
                    config["max_target_positions"], config["max_target_positions"]
                ),
                diagonal=1,
            ).bool(),
        )

        # weight's
        self.q_proj.weight.data.copy_(
            self.get_tensor(f"model.decoder.layers.{layer_no}.self_attn.q_proj.weight")
        )
        self.k_proj.weight.data.copy_(
            self.get_tensor(f"model.decoder.layers.{layer_no}.self_attn.k_proj.weight")
        )
        self.v_proj.weight.data.copy_(
            self.get_tensor(f"model.decoder.layers.{layer_no}.self_attn.v_proj.weight")
        )
        self.out_proj.weight.data.copy_(
            self.get_tensor(
                f"model.decoder.layers.{layer_no}.self_attn.out_proj.weight"
            )
        )

        # bias
        self.q_proj.bias.data.copy_(
            self.get_tensor(f"model.decoder.layers.{layer_no}.self_attn.q_proj.bias")
        )
        self.v_proj.bias.data.copy_(
            self.get_tensor(f"model.decoder.layers.{layer_no}.self_attn.v_proj.bias")
        )
        self.out_proj.bias.data.copy_(
            self.get_tensor(f"model.decoder.layers.{layer_no}.self_attn.out_proj.bias")
        )

    @torch.no_grad()
    def forward(self, x, past_kv: None):

        B, S, _ = x.shape

        q = self.q_proj(x)
        k = self.k_proj(x)
        v = self.v_proj(x)

        q = q.view(B, S, self.num_head, self.head_dim).transpose(1, 2)
        k = k.view(B, S, self.num_head, self.head_dim).transpose(1, 2)
        v = v.view(B, S, self.num_head, self.head_dim).transpose(1, 2)

        if past_kv is not None:
            past_k, past_v = past_kv

            k = torch.cat((past_k, k), dim=2)
            v = torch.cat((past_v, v), dim=2)

        present_kv = (k, v)

        attn_score = (q @ k.transpose(-2, -1)) * (self.head_dim**-0.5)

        if S > 1:
            attn_score = attn_score.masked_fill(self.mask[:S, :S], float("-inf"))

        wei = torch.nn.functional.softmax(attn_score, dim=-1)

        v_rep = wei @ v
        out = v_rep.transpose(1, 2).contiguous()
        out = out.view(B, S, self.d_model)

        out = self.out_proj(out)

        return out, present_kv

    def get_tensor(self, name):

        for f in self.files:
            if name in f.keys():
                return f.get_tensor(name)


class WhisperDecoderCrossAttention(torch.nn.Module):

    def __init__(self, config: dict, layer_no: int, safetensor_files: list):
        super().__init__()

        self.d_model = config["d_model"]
        self.num_head = config["decoder_attention_heads"]

        self.files = safetensor_files

        assert self.d_model % self.num_head == 0
        self.head_dim = self.d_model // self.num_head

        self.q_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.k_proj = torch.nn.Linear(self.d_model, self.d_model, bias=False)
        self.v_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.out_proj = torch.nn.Linear(self.d_model, self.d_model)

        # weight's
        self.q_proj.weight.data.copy_(
            self.get_tensor(
                f"model.decoder.layers.{layer_no}.encoder_attn.q_proj.weight"
            )
        )
        self.k_proj.weight.data.copy_(
            self.get_tensor(
                f"model.decoder.layers.{layer_no}.encoder_attn.k_proj.weight"
            )
        )
        self.v_proj.weight.data.copy_(
            self.get_tensor(
                f"model.decoder.layers.{layer_no}.encoder_attn.v_proj.weight"
            )
        )
        self.out_proj.weight.data.copy_(
            self.get_tensor(
                f"model.decoder.layers.{layer_no}.encoder_attn.out_proj.weight"
            )
        )

        # bias
        self.q_proj.bias.data.copy_(
            self.get_tensor(f"model.decoder.layers.{layer_no}.encoder_attn.q_proj.bias")
        )
        self.v_proj.bias.data.copy_(
            self.get_tensor(f"model.decoder.layers.{layer_no}.encoder_attn.v_proj.bias")
        )
        self.out_proj.bias.data.copy_(
            self.get_tensor(
                f"model.decoder.layers.{layer_no}.encoder_attn.out_proj.bias"
            )
        )

    @torch.no_grad()
    def forward(self, decoder_rep, encoder_rep, past_kv: None):

        DB, DS, _ = decoder_rep.shape
        EB, ES, _ = encoder_rep.shape

        if past_kv is not None:
            k, v = past_kv

        else:
            k = self.k_proj(encoder_rep)
            v = self.v_proj(encoder_rep)

            k = k.view(EB, ES, self.num_head, self.head_dim).transpose(1, 2)
            v = v.view(EB, ES, self.num_head, self.head_dim).transpose(1, 2)

        q = self.q_proj(decoder_rep)
        q = q.view(DB, DS, self.num_head, self.head_dim).transpose(1, 2)

        attn_score = (q @ k.transpose(-2, -1)) * (self.head_dim**-0.5)
        wei = torch.nn.functional.softmax(attn_score, dim=-1)

        v_rep = wei @ v
        out = v_rep.transpose(1, 2).contiguous()
        out = out.view(DB, DS, self.d_model)

        out = self.out_proj(out)

        return out, (k, v)

    def get_tensor(self, name):

        for file in self.files:
            if name in file.keys():
                return file.get_tensor(name)


class WhisperDecoderFeedForwardNeuralNetwork(torch.nn.Module):

    def __init__(self, config: dict, layer_no: int, safetensor_files: list):
        super().__init__()
        self.d_model = config["d_model"]
        self.d_ff = config["decoder_ffn_dim"]

        self.files = safetensor_files

        self.fc1 = torch.nn.Linear(in_features=self.d_model, out_features=self.d_ff)
        self.fc2 = torch.nn.Linear(in_features=self.d_ff, out_features=self.d_model)

        # weight's
        self.fc1.weight.data.copy_(
            self.get_tensor(f"model.decoder.layers.{layer_no}.fc1.weight")
        )
        self.fc2.weight.data.copy_(
            self.get_tensor(f"model.decoder.layers.{layer_no}.fc2.weight")
        )

        # bias
        self.fc1.bias.data.copy_(
            self.get_tensor(f"model.decoder.layers.{layer_no}.fc1.bias")
        )
        self.fc2.bias.data.copy_(
            self.get_tensor(f"model.decoder.layers.{layer_no}.fc2.bias")
        )

    @torch.no_grad()
    def forward(self, x):

        output = self.fc1(x)
        output = torch.nn.functional.gelu(output)

        return self.fc2(output)

    def get_tensor(self, name):

        for file in self.files:
            if name in file.keys():
                return file.get_tensor(name)


class WhisperDecoderLayer(torch.nn.Module):

    def __init__(self, config: dict, layer_no: int, safetensor_files: list):
        super().__init__()

        self.d_model = config["d_model"]
        self.files = safetensor_files

        self.decoder_mask_attn = WhisperDecoderMaskedAttention(
            config, layer_no, safetensor_files
        )
        self.decoder_cross_attn = WhisperDecoderCrossAttention(
            config, layer_no, safetensor_files
        )
        self.decoder_ffn = WhisperDecoderFeedForwardNeuralNetwork(
            config, layer_no, safetensor_files
        )

        # layer norm
        self.mask_attn_layer_norm = torch.nn.LayerNorm(self.d_model)
        self.cross_attn_layer_norm = torch.nn.LayerNorm(self.d_model)
        self.final_layer_norm = torch.nn.LayerNorm(self.d_model)

        # weight's
        self.mask_attn_layer_norm.weight.data.copy_(
            self.get_tensor(
                f"model.decoder.layers.{layer_no}.self_attn_layer_norm.weight"
            )
        )
        self.cross_attn_layer_norm.weight.data.copy_(
            self.get_tensor(
                f"model.decoder.layers.{layer_no}.encoder_attn_layer_norm.weight"
            )
        )
        self.final_layer_norm.weight.data.copy_(
            self.get_tensor(f"model.decoder.layers.{layer_no}.final_layer_norm.weight")
        )

        # bias
        self.mask_attn_layer_norm.bias.data.copy_(
            self.get_tensor(
                f"model.decoder.layers.{layer_no}.self_attn_layer_norm.bias"
            )
        )
        self.cross_attn_layer_norm.bias.data.copy_(
            self.get_tensor(
                f"model.decoder.layers.{layer_no}.encoder_attn_layer_norm.bias"
            )
        )
        self.final_layer_norm.bias.data.copy_(
            self.get_tensor(f"model.decoder.layers.{layer_no}.final_layer_norm.bias")
        )

    @torch.no_grad()
    def forward(
        self, from_decoder, from_encoder, masked_attn_kv: None, cross_attn_kv: None
    ):

        residual = from_decoder

        x, present_masked_attn_kv = self.decoder_mask_attn(
            self.mask_attn_layer_norm(residual), masked_attn_kv
        )
        x = residual + x

        residual = x

        x, present_cross_attn_kv = self.decoder_cross_attn(
            self.cross_attn_layer_norm(x), from_encoder, cross_attn_kv
        )
        x = residual + x

        x = x + self.decoder_ffn(self.final_layer_norm(x))

        return x, present_masked_attn_kv, present_cross_attn_kv

    def get_tensor(self, name):
        for file in self.files:
            if name in file.keys():
                return file.get_tensor(name)


class WhisperDecoder(torch.nn.Module):

    def __init__(self, config: dict, safetensor_files: list):
        super().__init__()

        self.model_config = config
        self.files = safetensor_files

        self.embed_tokens = torch.nn.Embedding(
            num_embeddings=self.model_config["vocab_size"],
            embedding_dim=self.model_config["d_model"],
            padding_idx=self.model_config["pad_token_id"],
        )
        self.embed_positions = torch.nn.Embedding(
            num_embeddings=self.model_config["max_target_positions"],
            embedding_dim=self.model_config["d_model"],
        )
        self.layers = torch.nn.ModuleList(
            [
                WhisperDecoderLayer(self.model_config, i, self.files)
                for i in range(self.model_config["decoder_layers"])
            ]
        )
        self.layer_norm = torch.nn.LayerNorm(self.model_config["d_model"])

        # weight's
        self.embed_tokens.weight.data.copy_(
            self.get_tensor("model.decoder.embed_tokens.weight")
        )
        self.embed_positions.weight.data.copy_(
            self.get_tensor("model.decoder.embed_positions.weight")
        )
        self.layer_norm.weight.data.copy_(
            self.get_tensor("model.decoder.layer_norm.weight")
        )
        # bias
        self.layer_norm.bias.data.copy_(
            self.get_tensor("model.decoder.layer_norm.bias")
        )
        # kv cache
        self.masked_attn_kv = [None] * self.model_config["decoder_layers"]
        self.cross_attn_kv = [None] * self.model_config["decoder_layers"]

        self.current_pos = None

    @torch.no_grad()
    def forward(self, from_decoder, from_encoder):

        x = self.embed_tokens(from_decoder)

        if self.current_pos is None:
            self.current_pos = x.size(1)
            positions = torch.arange(self.current_pos, device=x.device)
            x = x + self.embed_positions(positions)

        else:
            position = torch.tensor([self.current_pos], device=x.device)
            x = x + self.embed_positions(position)
            self.current_pos += 1

        for i, layer in enumerate(self.layers):
            x, self.masked_attn_kv[i], self.cross_attn_kv[i] = layer(
                x, from_encoder, self.masked_attn_kv[i], self.cross_attn_kv[i]
            )

        return self.layer_norm(x)

    def get_tensor(self, name):
        for file in self.files:
            if name in file.keys():
                return file.get_tensor(name)

    def clean_cache(self):
        self.masked_attn_kv = [None] * self.model_config["decoder_layers"]
        self.cross_attn_kv = [None] * self.model_config["decoder_layers"]
        self.current_pos = None


class WhisperSmall(torch.nn.Module):
    """
    Whisper Small is a lightweight STT model with approximately 244 million parameters.
    Officially, it supports mono audio clips of up to 30 seconds.
    """

    def __init__(self, config: dict, safetensor_files: list[str]):
        super().__init__()

        self.model_config = config

        self.bos_token_id = config["bos_token_id"]
        self.decoder_start_token_id = config["decoder_start_token_id"]
        self.eos_token_id = config["eos_token_id"]
        self.max_length = config["max_length"]

        # Whisper timestamp tokens
        self.timestamp_begin = 50364
        self.timestamp_rate = 0.02
        self.no_timestamps_token_id = 50363

        self.max_initial_timestamp = 1.0
        self.max_initial_timestamp_index = int(
            self.max_initial_timestamp / self.timestamp_rate
        )

        self.files = [
            safe_open(file, framework="pt", device="cpu") for file in safetensor_files
        ]

        self.encoder = WhisperEncoder(self.model_config, self.files)
        self.decoder = WhisperDecoder(self.model_config, self.files)

        # Tied output projection
        self.back_proj = torch.nn.Embedding(
            num_embeddings=self.model_config["vocab_size"],
            embedding_dim=self.model_config["d_model"],
        )

        self.back_proj.weight.data.copy_(
            self.get_tensor("model.decoder.embed_tokens.weight")
        )

    def is_timestamp_token(self, token_id):
        return token_id >= self.timestamp_begin

    def token_to_timestamp(self, token_id):
        return (token_id - self.timestamp_begin) * self.timestamp_rate

    def apply_timestamp_rules(self, logits, generated_tokens):

        logits = logits[:, -1, :]

        # Suppress <|notimestamps|>
        logits[:, self.no_timestamps_token_id] = -float("inf")

        # Timestamp rules
        if len(generated_tokens) > 0:

            last_was_timestamp = (
                len(generated_tokens) >= 1
                and generated_tokens[-1] >= self.timestamp_begin
            )

            penultimate_was_timestamp = (
                len(generated_tokens) < 2
                or generated_tokens[-2] >= self.timestamp_begin
            )

            # Timestamps have to appear in pairs
            if last_was_timestamp:

                if penultimate_was_timestamp:
                    # Two consecutive timestamps:
                    # next token must be normal text/EOT.
                    logits[:, self.timestamp_begin :] = -float("inf")

                else:
                    # One timestamp:
                    # next token must be another timestamp.
                    logits[:, : self.eos_token_id] = -float("inf")

            timestamps = torch.tensor(
                [token for token in generated_tokens if token >= self.timestamp_begin],
                device=logits.device,
            )

            if timestamps.numel() > 0:

                # Timestamps cannot decrease.
                #
                # If we just generated the first timestamp of a pair,
                # the second timestamp must be strictly greater.
                if last_was_timestamp and not penultimate_was_timestamp:

                    timestamp_last = timestamps[-1]

                else:

                    timestamp_last = timestamps[-1] + 1

                logits[:, self.timestamp_begin : timestamp_last] = -float("inf")

        # First generated token must be a timestamp
        if len(generated_tokens) == 0:

            logits[:, : self.timestamp_begin] = -float("inf")

            # Maximum initial timestamp = 1 second
            last_allowed = self.timestamp_begin + self.max_initial_timestamp_index

            logits[:, last_allowed + 1 :] = -float("inf")

        # If the combined probability of all timestamp tokens is
        # greater than the probability of the best text token,
        # force a timestamp.

        logprobs = torch.nn.functional.log_softmax(
            logits.float(),
            dim=-1,
        )

        timestamp_logprob = torch.logsumexp(
            logprobs[:, self.timestamp_begin :],
            dim=-1,
        )

        max_text_token_logprob = torch.max(
            logprobs[:, : self.timestamp_begin],
            dim=-1,
        ).values

        if timestamp_logprob[0] > max_text_token_logprob[0]:

            logits[:, : self.timestamp_begin] = -float("inf")

        return logits

    @torch.no_grad()
    def forward(
        self,
        audio_path: str,
        lang_id: int = 50259,
        task_id: int = 50359,
        return_timestamps: bool = False,
        device: torch.device = torch.device("cpu"),
    ):
        """
        Transcribe a single audio file at a time.

        NOTE: The model now supports audio inputs longer than 30 seconds.
            However, timestamp generation has not yet been implemented,
            causing timestamps to restart after every 30 seconds.

        Parameters
        ----------
        audio_file : str
            Path to the input audio file.

        lang : str
            Language code specifying the language of the audio.
            Refer to the official Hugging Face model repository for
            the complete list of supported language codes.

            Example: <|en|> : 50259

        task : str
            Specifies the transcription task:
            - "transcribe": Transcribe the audio in its original language.
            - "translate": Translate the audio into English.

            <|transcribe|> : 50359
            <|translate|>  : 50358

        device : str, default="cpu"
            Device on which the model will perform inference.
            Use "cuda" for GPU acceleration or "cpu" for CPU processing.

        return_timestamps : bool, default=False
            Whether to include timestamps in the transcription output.
        """

        transcribe_tokens = []

        for chunk in split_audio(audio_path):

            generated_tokens = []

            x = log_mel_spectrogram(pad_or_trim(chunk), device=device)

            encoder_output = self.encoder(x)

            prompt = [
                self.decoder_start_token_id,
                lang_id,
                task_id,
            ]

            if not return_timestamps:
                prompt.append(self.no_timestamps_token_id)

            decoder_input = torch.tensor([prompt], device=x.device)

            self.decoder.clean_cache()

            for _ in range(self.max_length):

                decoder_output = self.decoder(decoder_input, encoder_output)

                logits = decoder_output @ self.back_proj.weight.T

                if return_timestamps:
                    next_logits = self.apply_timestamp_rules(logits, generated_tokens)
                else:
                    next_logits = logits[:, -1, :].clone()

                    # Prevent timestamp generation
                    next_logits[:, self.timestamp_begin :] = -float("inf")

                predicted_token = torch.argmax(next_logits, dim=-1).item()

                if predicted_token == self.eos_token_id:
                    break

                generated_tokens.append(predicted_token)
                transcribe_tokens.append(predicted_token)

                decoder_input = torch.tensor(
                    [[predicted_token]],
                    device=decoder_output.device,
                )

        return transcribe_tokens

    def get_tensor(self, name):

        for file in self.files:
            if name in file.keys():
                return file.get_tensor(name)

        raise KeyError(f"Tensor not found: {name}")
