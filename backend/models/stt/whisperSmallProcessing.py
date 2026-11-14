# Implementing the same audio loading, trimming, and padding logic used in the original Whisper library.

import os
from math import gcd
from functools import lru_cache
from typing import Optional, Union
import logging

logger = logging.getLogger(__name__)


import numpy as np
from scipy.signal import resample_poly
import soundfile as sf
import torch
import torch.nn.functional as F

# hard-coded audio hyperparameters
SAMPLE_RATE = 16000
N_FFT = 400
HOP_LENGTH = 160
CHUNK_LENGTH = 30
N_SAMPLES = CHUNK_LENGTH * SAMPLE_RATE  # 480000 samples in a 30-second chunk
N_FRAMES = N_SAMPLES // HOP_LENGTH  # 3000 frames in a mel spectrogram input

N_SAMPLES_PER_TOKEN = HOP_LENGTH * 2  # the initial convolutions has stride 2
FRAMES_PER_SECOND = SAMPLE_RATE // HOP_LENGTH  # 10ms per audio frame
TOKENS_PER_SECOND = SAMPLE_RATE // N_SAMPLES_PER_TOKEN  # 20ms per audio token


def pad_or_trim(array, length: int = N_SAMPLES, *, axis: int = -1):
    """
    Pad or trim the audio array to N_SAMPLES, as expected by the encoder.
    """
    if torch.is_tensor(array):
        if array.shape[axis] > length:
            array = array.index_select(
                dim=axis, index=torch.arange(length, device=array.device)
            )

        if array.shape[axis] < length:
            pad_widths = [(0, 0)] * array.ndim
            pad_widths[axis] = (0, length - array.shape[axis])
            array = F.pad(array, [pad for sizes in pad_widths[::-1] for pad in sizes])
    else:
        if array.shape[axis] > length:
            array = array.take(indices=range(length), axis=axis)

        if array.shape[axis] < length:
            pad_widths = [(0, 0)] * array.ndim
            pad_widths[axis] = (0, length - array.shape[axis])
            array = np.pad(array, pad_widths)

    return array


@lru_cache(maxsize=None)
def mel_filters(device, n_mels: int) -> torch.Tensor:
    """
    load the mel filterbank matrix for projecting STFT into a Mel spectrogram.
    Allows decoupling librosa dependency; saved using:

        np.savez_compressed(
            "mel_filters.npz",
            mel_80=librosa.filters.mel(sr=16000, n_fft=400, n_mels=80),
            mel_128=librosa.filters.mel(sr=16000, n_fft=400, n_mels=128),
        )
    """
    assert n_mels in {80, 128}, f"Unsupported n_mels: {n_mels}"

    # This may cause build issues because the file is not included in the build.
    filters_path = (
        "/home/vishwjeet/Desktop/Projects/LinguSync/backend/models/stt/mel_filters.npz"
    )

    with np.load(filters_path, allow_pickle=False) as f:
        return torch.from_numpy(f[f"mel_{n_mels}"]).to(device)


def log_mel_spectrogram(
    audio: Union[np.ndarray, torch.Tensor],
    n_mels: int = 80,
    padding: int = 0,
    device: Optional[Union[str, torch.device]] = None,
):
    """
    Compute the log-Mel spectrogram of

    Parameters
    ----------
    audio: Union[np.ndarray, torch.Tensor], shape = (*)
        NumPy array or Tensor containing the audio waveform in 16 kHz

    n_mels: int
        The number of Mel-frequency filters, only 80 and 128 are supported

    padding: int
        Number of zero samples to pad to the right

    device: Optional[Union[str, torch.device]]
        If given, the audio tensor is moved to this device before STFT

    Returns
    -------
    torch.Tensor, shape = (1, n_mels, n_frames)
        A Tensor that contains the Mel spectrogram
    """
    if not torch.is_tensor(audio):
        audio = torch.from_numpy(audio)

    if device is not None:
        audio = audio.to(device)
    if padding > 0:
        audio = F.pad(audio, (0, padding))
    window = torch.hann_window(N_FFT).to(audio.device)
    stft = torch.stft(audio, N_FFT, HOP_LENGTH, window=window, return_complex=True)
    magnitudes = stft[..., :-1].abs() ** 2

    filters = mel_filters(audio.device, n_mels)
    mel_spec = filters @ magnitudes

    log_spec = torch.clamp(mel_spec, min=1e-10).log10()
    log_spec = torch.maximum(log_spec, log_spec.max() - 8.0)
    log_spec = (log_spec + 4.0) / 4.0

    return log_spec.unsqueeze(0)


def split_audio(file: str, sr: int = 16000, chunk_duration: int = 30) -> list:
    """
    Split the input audio file into fixed-duration chunks.

    Parameters
    ----------
    file : str
        Path to the input audio file.

    sr : int, default=16000
        Sample rate of the output audio in Hz.

    chunk_duration : int, default=30
        Duration of each audio chunk in seconds.

    Returns
    -------
    list[np.ndarray]
        A list of audio chunks represented as NumPy arrays.
        Each chunk contains mono, float32 audio at the specified sample rate.
    """

    # Load audio
    audio, original_sr = sf.read(file, dtype="float32")

    # Convert stereo to mono
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    # Resample if necessary
    if original_sr != sr:
        divisor = gcd(original_sr, sr)
        audio = resample_poly(audio, sr // divisor, original_sr // divisor).astype(
            np.float32
        )

    # Split into chunks
    chunk_size = chunk_duration * sr

    chunks = [
        audio[start : start + chunk_size] for start in range(0, len(audio), chunk_size)
    ]

    return chunks


def save_transcript(
    script: str = None, file_name: str = "transcript.txt", save_dir: str = None
) -> bool:
    """
    Save the speech-to-text model's generated transcript (output) to a text file.

    Parameters
    ----------
    script : str, default=None
        Transcript or translation generated by the STT model.

    file_name : str, default="transcript.txt"
        Name of the file to save the transcript as.

    save_dir : str, default=None
        Path to the directory where the file should be saved.

    Returns
    -------
    str
        Path to the saved transcript file.
    """

    try:

        if not save_dir or not os.path.isdir(save_dir):
            raise FileNotFoundError(f"Directory not found: {save_dir}")

        file_path = os.path.join(save_dir, file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(script)

        return file_path

    except Exception as E:
        logger.error(E)
        return None
