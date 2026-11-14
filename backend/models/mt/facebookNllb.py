# The beta version is being developed using PyTorch.
# In future versions, I'll replace PyTorch with lightweight libraries
# to perform the required operations and reduce the final application size.

import math

import torch


class SinusoidalPositionalEmbedding(torch.nn.Module):
    """ "Sinusoidal positional encoding."""

    def __init__(
        self,
        num_positions: int,
        embedding_dim: int,
        padding_idx: int | None = None,
    ):
        super().__init__()

        self.offset = 2
        self.num_positions = num_positions
        self.embedding_dim = embedding_dim
        self.padding_idx = padding_idx

        self.register_buffer(
            "weights",
            self.get_embedding(
                num_positions + self.offset,
                embedding_dim,
                padding_idx,
            ),
            persistent=False,
        )

    @staticmethod
    def get_embedding(
        num_embeddings: int,
        embedding_dim: int,
        padding_idx: int | None = None,
    ):

        half_dim = embedding_dim // 2

        exponent = math.log(10000.0) / (half_dim - 1)

        frequencies = torch.exp(torch.arange(half_dim, dtype=torch.float32) * -exponent)

        positions = torch.arange(num_embeddings, dtype=torch.float32).unsqueeze(1)

        angles = positions * frequencies.unsqueeze(0)

        embeddings = torch.cat(
            [torch.sin(angles), torch.cos(angles)],
            dim=1,
        )

        if embedding_dim % 2 == 1:
            embeddings = torch.cat(
                [
                    embeddings,
                    torch.zeros(num_embeddings, 1),
                ],
                dim=1,
            )

        if padding_idx is not None:
            embeddings[padding_idx, :] = 0

        return embeddings

    @staticmethod
    def create_position_ids_from_input_ids(
        input_ids: torch.Tensor,
        padding_idx: int,
        past_key_values_length: int = 0,
    ):

        mask = input_ids.ne(padding_idx).int()

        incremental_indices = torch.cumsum(mask, dim=1) + past_key_values_length

        return (incremental_indices * mask).long() + padding_idx

    @torch.no_grad()
    def forward(
        self,
        input_ids: torch.Tensor,
        past_key_values_length: int = 0,
    ):

        position_ids = self.create_position_ids_from_input_ids(
            input_ids,
            self.padding_idx,
            past_key_values_length,
        )

        max_position = position_ids.max().item()

        if max_position >= self.weights.size(0):
            raise ValueError(
                f"Position {max_position} exceeds positional "
                f"embedding table size {self.weights.size(0)}"
            )

        return self.weights.to(input_ids.device)[position_ids]


class MultiHeadAtention(torch.nn.Module):

    def __init__(self, config: dict, layer_no: int, state_dict: dict):
        super().__init__()

        self.d_model = config["d_model"]
        self.num_attn_head = config["encoder_attention_heads"]
        self.attn_dim = self.d_model // self.num_attn_head

        self.k_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.q_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.v_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.out_proj = torch.nn.Linear(self.d_model, self.d_model)

        # weight
        self.k_proj.weight.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.self_attn.k_proj.weight"]
        )
        self.q_proj.weight.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.self_attn.q_proj.weight"]
        )
        self.v_proj.weight.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.self_attn.v_proj.weight"]
        )
        self.out_proj.weight.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.self_attn.out_proj.weight"]
        )

        # bias
        self.k_proj.bias.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.self_attn.k_proj.bias"]
        )
        self.q_proj.bias.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.self_attn.q_proj.bias"]
        )
        self.v_proj.bias.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.self_attn.v_proj.bias"]
        )
        self.out_proj.bias.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.self_attn.out_proj.bias"]
        )

    @torch.no_grad()
    def forward(self, x):
        B, S, _ = x.shape

        q = self.q_proj(x).view(B, S, self.num_attn_head, self.attn_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, S, self.num_attn_head, self.attn_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, S, self.num_attn_head, self.attn_dim).transpose(1, 2)

        attn_scores = q @ k.transpose(-2, -1) * (self.attn_dim**-0.5)
        attn_scores = torch.nn.functional.softmax(attn_scores, dim=-1)

        out = attn_scores @ v
        out = out.transpose(1, 2).contiguous().view(B, S, self.d_model)

        return self.out_proj(out)


class EncoderFeedForwardNetwork(torch.nn.Module):

    def __init__(self, config: dict, layer_no: int, state_dict: dict):
        super().__init__()

        self.d_model = config["d_model"]
        self.ffn_dim = config["encoder_ffn_dim"]

        self.fc1 = torch.nn.Linear(in_features=self.d_model, out_features=self.ffn_dim)
        self.act = torch.nn.ReLU()
        self.fc2 = torch.nn.Linear(in_features=self.ffn_dim, out_features=self.d_model)

        # weight
        self.fc1.weight.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.fc1.weight"]
        )
        self.fc2.weight.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.fc2.weight"]
        )

        # bias
        self.fc1.bias.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.fc1.bias"]
        )
        self.fc2.bias.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.fc2.bias"]
        )

    @torch.no_grad()
    def forward(self, x):

        return self.fc2(self.act(self.fc1(x)))


class EncoderLayer(torch.nn.Module):

    def __init__(self, config: dict, layer_no: int, state_dict: dict):
        super().__init__()
        self.d_model = config["d_model"]

        self.self_attn_layer_norm = torch.nn.LayerNorm(self.d_model)
        self.self_attn = MultiHeadAtention(config, layer_no, state_dict)
        self.ffn = EncoderFeedForwardNetwork(config, layer_no, state_dict)
        self.final_layer_norm = torch.nn.LayerNorm(self.d_model)

        # weight
        self.self_attn_layer_norm.weight.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.self_attn_layer_norm.weight"]
        )
        self.final_layer_norm.weight.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.final_layer_norm.weight"]
        )

        # bias
        self.self_attn_layer_norm.bias.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.self_attn_layer_norm.bias"]
        )
        self.final_layer_norm.bias.data.copy_(
            state_dict[f"model.encoder.layers.{layer_no}.final_layer_norm.bias"]
        )

    @torch.no_grad()
    def forward(self, x):

        residual = x
        x = residual + self.self_attn(self.self_attn_layer_norm(x))

        residual = x
        return residual + self.ffn(self.final_layer_norm(x))


class NllbEncoder(torch.nn.Module):
    """NLLB encoder architecture."""

    def __init__(self, config: dict, state_dict: dict):
        super().__init__()

        self.token_embed = torch.nn.Embedding(
            num_embeddings=config["vocab_size"],
            embedding_dim=config["d_model"],
            padding_idx=config["pad_token_id"],
        )

        self.embed_scale = (
            math.sqrt(config["d_model"]) if config["scale_embedding"] else 1.0
        )

        self.embed_positions = SinusoidalPositionalEmbedding(
            num_positions=config["max_position_embeddings"],
            embedding_dim=config["d_model"],
            padding_idx=config["pad_token_id"],
        )

        self.layers = torch.nn.ModuleList(
            EncoderLayer(config, i, state_dict) for i in range(config["encoder_layers"])
        )

        self.final_layer_norm = torch.nn.LayerNorm(config["d_model"])

        # weight
        self.token_embed.weight.data.copy_(
            state_dict["model.encoder.embed_tokens.weight"]
        )
        self.final_layer_norm.weight.data.copy_(
            state_dict["model.encoder.layer_norm.weight"]
        )

        # bias
        self.final_layer_norm.bias.data.copy_(
            state_dict["model.encoder.layer_norm.bias"]
        )

    @torch.no_grad()
    def forward(self, x):

        positions = self.embed_positions(x)

        x = self.token_embed(x) * self.embed_scale
        x = x + positions.to(dtype=x.dtype)

        for layer in self.layers:
            x = layer(x)

        return self.final_layer_norm(x)


class MaskedMultiHeadAttention(torch.nn.Module):
    def __init__(self, config: dict, layer_no: int, state_dict: dict):
        super().__init__()

        self.d_model = config["d_model"]
        self.num_attn_head = config["decoder_attention_heads"]
        self.attn_dim = self.d_model // self.num_attn_head

        self.q_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.k_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.v_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.out_proj = torch.nn.Linear(self.d_model, self.d_model)

        # weight
        self.q_proj.weight.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.self_attn.q_proj.weight"]
        )
        self.k_proj.weight.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.self_attn.k_proj.weight"]
        )
        self.v_proj.weight.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.self_attn.v_proj.weight"]
        )
        self.out_proj.weight.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.self_attn.out_proj.weight"]
        )

        # bias
        self.q_proj.bias.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.self_attn.q_proj.bias"]
        )
        self.k_proj.bias.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.self_attn.k_proj.bias"]
        )
        self.v_proj.bias.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.self_attn.v_proj.bias"]
        )
        self.out_proj.bias.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.self_attn.out_proj.bias"]
        )

    def forward(self, x, past_kv=None):

        B, S, _ = x.shape

        q = self.q_proj(x).view(B, S, self.num_attn_head, self.attn_dim).transpose(1, 2)
        k = self.k_proj(x).view(B, S, self.num_attn_head, self.attn_dim).transpose(1, 2)
        v = self.v_proj(x).view(B, S, self.num_attn_head, self.attn_dim).transpose(1, 2)

        if past_kv:
            past_k, past_v = past_kv

            k = torch.cat((past_k, k), dim=2)
            v = torch.cat((past_v, v), dim=2)

        present_kv = (k, v)

        attn_scores = (q @ k.transpose(-2, -1)) * (self.attn_dim**-0.5)

        if S > 1:
            mask = torch.triu(torch.ones(S, S), diagonal=1).bool()
            attn_scores = attn_scores.masked_fill(mask, float("-inf"))

        attn_scores = torch.nn.functional.softmax(attn_scores, dim=-1)

        out = attn_scores @ v
        out = out.transpose(1, 2).contiguous().view(B, S, self.d_model)

        return self.out_proj(out), present_kv


class CrossAttention(torch.nn.Module):

    def __init__(self, config: dict, layer_no: int, state_dict: dict):
        super().__init__()

        self.d_model = config["d_model"]
        self.num_attn_head = config["decoder_attention_heads"]
        self.attn_dim = self.d_model // self.num_attn_head

        self.q_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.k_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.v_proj = torch.nn.Linear(self.d_model, self.d_model)
        self.out_proj = torch.nn.Linear(self.d_model, self.d_model)

        # weight
        self.q_proj.weight.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.encoder_attn.q_proj.weight"]
        )
        self.k_proj.weight.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.encoder_attn.k_proj.weight"]
        )
        self.v_proj.weight.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.encoder_attn.v_proj.weight"]
        )
        self.out_proj.weight.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.encoder_attn.out_proj.weight"]
        )

        # bias
        self.q_proj.bias.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.encoder_attn.q_proj.bias"]
        )
        self.k_proj.bias.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.encoder_attn.k_proj.bias"]
        )
        self.v_proj.bias.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.encoder_attn.v_proj.bias"]
        )
        self.out_proj.bias.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.encoder_attn.out_proj.bias"]
        )

    def forward(self, decoder_rep, encoder_rep) -> torch.Tensor:

        B, S, _ = decoder_rep.shape

        q = (
            self.q_proj(decoder_rep)
            .view(B, S, self.num_attn_head, self.attn_dim)
            .transpose(1, 2)
        )
        k = (
            self.k_proj(encoder_rep)
            .view(
                encoder_rep.size(0),
                encoder_rep.size(1),
                self.num_attn_head,
                self.attn_dim,
            )
            .transpose(1, 2)
        )
        v = (
            self.v_proj(encoder_rep)
            .view(
                encoder_rep.size(0),
                encoder_rep.size(1),
                self.num_attn_head,
                self.attn_dim,
            )
            .transpose(1, 2)
        )

        attn_score = q @ k.transpose(-2, -1) * (self.attn_dim**-0.5)
        attn_score = torch.nn.functional.softmax(attn_score, dim=-1)

        out = attn_score @ v
        out = out.transpose(1, 2).contiguous().view(B, S, self.d_model)

        return self.out_proj(out)


class DecoderFeedForwardNetwork(torch.nn.Module):

    def __init__(self, config: dict, layer_no: int, state_dict: dict):
        super().__init__()

        self.d_model = config["d_model"]
        self.ffn_dim = config["decoder_ffn_dim"]

        self.fc1 = torch.nn.Linear(in_features=self.d_model, out_features=self.ffn_dim)
        self.act = torch.nn.ReLU()
        self.fc2 = torch.nn.Linear(in_features=self.ffn_dim, out_features=self.d_model)

        # weight
        self.fc1.weight.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.fc1.weight"]
        )
        self.fc2.weight.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.fc2.weight"]
        )

        # bias
        self.fc1.bias.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.fc1.bias"]
        )
        self.fc2.bias.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.fc2.bias"]
        )

    @torch.no_grad()
    def forward(self, x):

        return self.fc2(self.act(self.fc1(x)))


class DecoderLayer(torch.nn.Module):

    def __init__(self, config: dict, layer_no: int, state_dict: dict):
        super().__init__()

        self.d_model = config["d_model"]

        self.ln1 = torch.nn.LayerNorm(self.d_model)
        self.masked_attn = MaskedMultiHeadAttention(config, layer_no, state_dict)
        self.ln2 = torch.nn.LayerNorm(self.d_model)
        self.cross_attn = CrossAttention(config, layer_no, state_dict)
        self.ln3 = torch.nn.LayerNorm(self.d_model)
        self.ffn = DecoderFeedForwardNetwork(config, layer_no, state_dict)

        # weight
        self.ln1.weight.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.self_attn_layer_norm.weight"]
        )
        self.ln2.weight.data.copy_(
            state_dict[
                f"model.decoder.layers.{layer_no}.encoder_attn_layer_norm.weight"
            ]
        )
        self.ln3.weight.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.final_layer_norm.weight"]
        )

        # bias
        self.ln1.bias.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.self_attn_layer_norm.bias"]
        )
        self.ln2.bias.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.encoder_attn_layer_norm.bias"]
        )
        self.ln3.bias.data.copy_(
            state_dict[f"model.decoder.layers.{layer_no}.final_layer_norm.bias"]
        )

    @torch.no_grad()
    def forward(self, deoder_input, encoder_output, past_kv=None):

        residual = deoder_input
        x, present_kv = self.masked_attn(self.ln1(deoder_input), past_kv)
        x = residual + x

        residual = x
        x = residual + self.cross_attn(self.ln2(x), encoder_output)

        residual = x

        return residual + self.ffn(self.ln3(x)), present_kv


class NllbDecoder(torch.nn.Module):
    """NLLB decoder architecture."""

    def __init__(self, config: dict, state_dict: dict):
        super().__init__()

        self.config = config

        self.pos_encoding = SinusoidalPositionalEmbedding(
            num_positions=config["max_position_embeddings"],
            embedding_dim=config["d_model"],
            padding_idx=config["pad_token_id"],
        )

        self.embed_scale = (
            math.sqrt(config["d_model"]) if config["scale_embedding"] else 1.0
        )

        self.token_embed = torch.nn.Embedding(  # lm head
            num_embeddings=config["vocab_size"],
            embedding_dim=config["d_model"],
            padding_idx=config["pad_token_id"],
        )
        self.layers = torch.nn.ModuleList(
            DecoderLayer(config, i, state_dict) for i in range(config["decoder_layers"])
        )
        self.final_layer_norm = torch.nn.LayerNorm(config["d_model"])

        self.kv_cache = [None] * config["decoder_layers"]

        # weight
        self.token_embed.weight.data.copy_(
            state_dict["model.decoder.embed_tokens.weight"]
        )
        self.final_layer_norm.weight.data.copy_(
            state_dict["model.decoder.layer_norm.weight"]
        )

        # bias
        self.final_layer_norm.bias.data.copy_(
            state_dict["model.decoder.layer_norm.bias"]
        )

    @torch.no_grad()
    def forward(self, decoder_input, encoder_output):

        past_length = 0
        if self.kv_cache[0] is not None:
            past_k, _ = self.kv_cache[0]
            past_length = past_k.shape[2]

        position_embeddings = self.pos_encoding(
            decoder_input, past_key_values_length=past_length
        )

        x = self.token_embed(decoder_input) * self.embed_scale
        x = x + position_embeddings.to(dtype=x.dtype)

        for i, layer in enumerate(self.layers):
            x, self.kv_cache[i] = layer(x, encoder_output, self.kv_cache[i])

        logits = self.final_layer_norm(x) @ self.token_embed.weight.data.T

        return torch.argmax(logits[:, -1, :], dim=-1)

    def clear_kv_cache(self):
        self.kv_cache = [None] * self.config["decoder_layers"]


class EncoderDecoder:
    """
    The encoder-decoder architecture allows the model to avoid loading the
    entire model into memory at once during inference. Instead, it splits
    the model into separate encoder and decoder components, allowing them
    to be loaded independently as needed.

    Parameters
    ----------
    config : dict
        Official configuration dictionary of the model.

    state_dict : dict
        Path to the model weights file.
    """

    def __init__(self, config: dict, state_dict: dict):
        self.config = config
        self.sd = state_dict

    def get_encoder(self, device: torch.device = torch.device("cpu")):
        """Returns the encoder on the specified device."""
        return NllbEncoder(self.config, self.sd).to(device)

    def get_decoder(self, device: torch.device = torch.device("cpu")):
        """Returns the decoder on the specified device."""
        return NllbDecoder(self.config, self.sd).to(device)


class FacebookNllb(torch.nn.Module):
    """
    NLLB is a machine translation model developed by Meta that supports over 200 languages.
    The 1.3B variant contains 1.3 billion parameters.
    It takes a text string in the source language and translates it into the target language.

    Visit the following link to see the list of supported languages:
    https://huggingface.co/facebook/nllb-200-1.3B/blob/main/special_tokens_map.json

    Parameters
    ----------
    config : dict
        Path to the official model configuration file.

    state_dict : dict
        Path to the model weights file (.bin).

    Returns
    -------
    str
        The translated transcript in the target language.
    """

    def __init__(self, config: dict, state_dict: dict):
        super().__init__()

        self.blocks = EncoderDecoder(config, state_dict)
        self.max_length = config["max_length"]
        self.bos_id = config["decoder_start_token_id"]
        self.eos_id = config["eos_token_id"]

    @torch.inference_mode()
    def forward(
        self,
        source_txt: str,
        target_lang_id: int,
        device: torch.device = torch.device("cpu"),
    ) -> str:
        """
        Translates the given transcript into the target language.
        Processes one transcript at a time.

        Parameters
        ----------
        source_txt : str
            Path to the source language text file.

        target_lang_id : int
            Language ID/code of the target language into which the
            input transcript will be translated.

        device : torch.device, default="cpu"
            Device on which the model performs inference.
            Use "cuda" for GPU acceleration or "cpu" for CPU processing.

        Returns
        -------
        str
            Translated transcript.
        """

        x = None  # For Now settin input = None

        model = self.blocks.get_encoder().to(x.device)
        encoder_output = model(x)

        model.cpu()
        del model
        torch.cuda.empty_cache()

        model = self.blocks.get_decoder().to(x.device)
        model.clear_kv_cache()

        decoder_input = self.bos_id
        predicted_seq = [target_lang_id]

        for step in range(self.max_length):
            predicted_token = model(
                torch.tensor([[decoder_input]], device=x.device), encoder_output
            ).item()

            if step == 0:
                decoder_input = target_lang_id
                continue

            if predicted_token == self.eos_id:
                break

            predicted_seq.append(predicted_token)
            decoder_input = predicted_token

        return predicted_seq
