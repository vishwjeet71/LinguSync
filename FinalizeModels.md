## Models

The following models have been finalized for use in this project. They are selected based on the trade-off between **performance** and **resource efficiency**.

| Task                     | Performance        | Efficient            |
| ------------------------ | ------------------ | -------------------- |
| **Speech-to-Text (STT)** | Whisper Large-v3   | **Qwen3-ASR 0.6B**   |
| **Translation**          | MADLAD-400 3B      | NLLB-200 1.3B        |
| **Text-to-Speech (TTS)** | **Qwen3-TTS 1.7B** | **OuteTTS 0.2 500M** |

### llama.cpp Compatibility

| Task            | Performance        | Efficient            |
| --------------- | ------------------ | -------------------- |
| **STT**         | Whisper Large-v3   | **Qwen3-ASR 0.6B**   |
| **Translation** | MADLAD-400 3B      | NLLB-200 1.3B        |
| **TTS**         | **Qwen3-TTS 1.7B** | **OuteTTS 0.2 500M** |