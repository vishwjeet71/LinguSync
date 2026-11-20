import json, uuid, os, asyncio, gc
import logging
from typing import Literal
from pathlib import Path

import torch

from backend.models.stt.whisperSmall import WhisperSmall
from backend.models.stt.whisperSmallProcessing import save_transcript
from backend.models.mt.facebookNllb import FacebookNllb
from backend.models.mt.facebookNllbProcessing import save_translation
from backend.models.tts.outeTTS import Outetts
from backend.models.tts.outeTTSProcessing import save_wav
from backend.models.tts.speechCodeDecoder import load_decoder
from backend.appDataBase.ApplicationSql import add_sql_data

logger = logging.getLogger(__name__)


class TranslationPipeline:
    """
    Handle the entire translation pipeline,
    from speech-to-text transcription to audio generation in the target language.

    Parameters
    ----------
    data_dir : str
        Root directory where the system stores model data.

    hardware_type : str, default="e"
        Hardware configuration to use (efficient or performance).
    """

    def __init__(
        self,
        data_dir: str,
        device: torch.device = torch.device("cpu"),
        hardware_type: Literal["e", "p"] = "e",
    ):

        self.app_data_dir = data_dir
        self.device = device
        self.ht = hardware_type
        self.sys_models_dir = os.path.join(data_dir, "models")

        self.translation_tasks = {}
        self.model = None

        # Prevent concurrent pipelines from using the shared model.
        self._pipeline_lock = asyncio.Lock()

        if not os.path.exists(self.sys_models_dir):
            raise FileNotFoundError(
                f"Models directory does not exist: {self.sys_models_dir}"
            )

        if self.ht not in ("e", "p"):
            raise ValueError("hardware_type must be either 'e' or 'h'")

        # efficient models
        self.whisper_small_dir = os.path.join(self.sys_models_dir, "whisper-small")
        self.nllb_dir = os.path.join(self.sys_models_dir, "nllb-200-1.3B")
        self.OuteTTS = os.path.join(self.sys_models_dir, "OuteTTS-0.2-500M")

    async def _run_blocking(self, func, *args, **kwargs):

        worker = asyncio.create_task(asyncio.to_thread(func, *args, **kwargs))

        try:
            return await asyncio.shield(worker)
        except asyncio.CancelledError:

            # The thread cannot be forcefully stopped.
            # Wait until the current operation safely finishes.
            try:
                await asyncio.shield(worker)
            except Exception:
                pass

            raise

    async def create_task(
        self,
        input_audio_path: str = None,
        project_id: int = None,
        project_name: str = None,
        source_language: str = None,
        target_language: str = None,
    ):

        if not input_audio_path or not os.path.exists(input_audio_path):
            raise FileNotFoundError(f"Unable to locate input audio: {input_audio_path}")

        project_dir = os.path.join(self.app_data_dir, "projects", project_name)
        os.makedirs(project_dir, exist_ok=True)

        task_id = str(uuid.uuid4())

        task_details = {
            "id": task_id,
            "hardware": self.ht,
            "inference_type": self.device.type,
            "current_working_task": None,  # stt, mt, tts, done
            "status": "queued",
            "task": None,
            "error": None,
        }

        self.translation_tasks[task_id] = task_details

        task = asyncio.create_task(
            self._run_pipeline(task_id, input_audio_path, project_id, project_dir),
            name=f"translation-{task_id}",
        )

        task_details["task"] = task

        return task_id

    async def _run_pipeline(
        self,
        task_id: str,
        input_audio_path: str,
        project_id: int = None,
        project_dir: str = None,
        source_lang_token: str = "hin_Deva",
        target_lang_token: str = "eng_Latn",
    ):

        task_info = self.translation_tasks[task_id]

        try:

            # Only one pipeline can use the shared model at a time.
            async with self._pipeline_lock:

                self._check_cancelled()

                if self.ht == "p":
                    logger.info(
                        "Performance model integration is not supported yet. Falling back to the efficient model."
                    )

                # STT
                task_info["current_working_task"] = "Speech-to-Text"
                task_info["status"] = "Loading STT Model..."

                await self._run_blocking(self._call_whisper_small)
                self._check_cancelled()

                task_info["status"] = "Extracting Transcript..."
                transcript = await self._run_blocking(
                    self.model,
                    audio_path=input_audio_path,
                    device=self.device,
                )
                transcript_saved_location = await self._run_blocking(
                    save_transcript,
                    script=transcript,
                    save_dir=project_dir,
                )

                await self._clear_model_space()
                self._check_cancelled()

                if not transcript_saved_location:
                    raise RuntimeError("Unable to save transcription file.")

                await self._run_blocking(
                    add_sql_data,
                    table_name="projects",
                    update=True,
                    row_id=project_id,
                    data={"stt_output": transcript_saved_location},
                )

                # MT
                task_info["current_working_task"] = "Machine Translation"
                task_info["status"] = "Loading MT Model..."

                await self._run_blocking(self._call_meta_nllb)
                self._check_cancelled()

                task_info["status"] = "Translating Transcript..."
                translation = await self._run_blocking(
                    self.model,
                    source_txt=transcript_saved_location,
                    source_lang_token=source_lang_token,
                    target_lang_token=target_lang_token,
                    device=self.device,
                )
                translation_saved_location = await self._run_blocking(
                    save_translation,
                    translation=translation,
                    save_dir=project_dir,
                )

                await self._clear_model_space()
                self._check_cancelled()

                if not translation_saved_location:
                    raise RuntimeError("Unable to save translation file.")

                await self._run_blocking(
                    add_sql_data,
                    table_name="projects",
                    update=True,
                    row_id=project_id,
                    data={"trans_output": translation_saved_location},
                )

                # TTS
                task_info["current_working_task"] = "Text-to-Speech"
                task_info["status"] = "Loading TTS Model..."

                await self._run_blocking(self._call_outeTTS)
                self._check_cancelled()

                task_info["status"] = "Generating speech codes..."
                speech_codes = await self._run_blocking(
                    self.model,
                    script_path=translation_saved_location,
                )

                await self._clear_model_space()
                self._check_cancelled()

                # AUDIO DECODER
                task_info["current_working_task"] = "Speech Generation"
                task_info["status"] = "Loading Audio Decoder..."

                await self._run_blocking(self._call_audio_decoder)
                self._check_cancelled()

                task_info["status"] = "Generating audio..."
                audio = torch.tensor(
                    [speech_codes],
                    device=self.device,
                )
                audio_result = await self._run_blocking(
                    self.model,
                    audio,
                )

                audio_saved_location = await self._run_blocking(
                    save_wav,
                    path=project_dir,
                    audio=audio_result,
                )

                await self._clear_model_space()
                self._check_cancelled()

                if not audio_saved_location:
                    raise RuntimeError("Unable to save generated audio.")

                await self._run_blocking(
                    add_sql_data,
                    table_name="projects",
                    update=True,
                    row_id=project_id,
                    data={
                        "tts_output": audio_saved_location,
                        "final_output": audio_saved_location,
                    },
                )

                task_info["status"] = "Completed"
                task_info["current_working_task"] = "Done"

                logger.info(
                    "Translation pipeline completed: %s",
                    task_id,
                )

        except asyncio.CancelledError:

            task_info["status"] = "cancelled"
            task_info["error"] = "Task cancelled by user."

            logger.info("Pipeline cancelled: %s", task_id)
            raise

        except Exception as error:

            task_info["status"] = "failed"
            task_info["error"] = str(error)

            logger.exception(
                "Pipeline failed: %s",
                task_id,
            )
        finally:
            await self._clear_model_space()

            if project_id is not None:
                try:
                    await self._run_blocking(
                        add_sql_data,
                        table_name="projects",
                        update=True,
                        row_id=project_id,
                        data={"processing_id": None},
                    )
                except Exception:
                    logger.exception(
                        "Failed to reset processing_id for project %s",
                        project_id,
                    )

    def _check_cancelled(self):

        current_task = asyncio.current_task()

        if current_task and current_task.cancelling():
            raise asyncio.CancelledError

    async def _clear_model_space(self):

        model = self.model
        self.model = None

        if model is not None:
            del model

        if self.device.type == "cuda":
            await self._run_blocking(torch.cuda.empty_cache)

        await self._run_blocking(gc.collect)

    async def cancel_task(self, task_id: str):

        task_info = self.translation_tasks.get(task_id)
        if not task_info:
            return False

        task = task_info.get("task")
        if not task or task.done():
            return False

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        return True

    def get_task_details(self, task_id: str):

        task_info = self.translation_tasks.get(task_id)
        if not task_info:
            return None

        return {key: value for key, value in task_info.items() if key != "task"}

    def _call_whisper_small(self):

        config_path = os.path.join(self.whisper_small_dir, "config.json")
        toknizer_path = os.path.join(self.whisper_small_dir, "tokenizer.json")
        model_weight_path = os.path.join(self.whisper_small_dir, "model.safetensors")

        for p in [config_path, toknizer_path, model_weight_path]:
            if not os.path.exists(p):
                logger.error(f"Path not Exist {p}")
                raise FileNotFoundError(f"Unable to locate path {p}")

        self.model = WhisperSmall(
            config=json.load(open(config_path)),
            tokenizer=toknizer_path,
            safetensor_files=[model_weight_path],
        ).to(self.device)

    def _call_meta_nllb(self):
        config_path = os.path.join(self.nllb_dir, "config.json")
        toknizer_path = os.path.join(self.nllb_dir, "tokenizer.json")
        model_weight_path = os.path.join(self.nllb_dir, "pytorch_model.bin")

        for p in [config_path, toknizer_path, model_weight_path]:
            if not os.path.exists(p):
                logger.error(f"Path not Exist {p}")
                raise FileNotFoundError(f"Unable to locate path {p}")

        self.model = FacebookNllb(
            config=json.load(open(config_path)),
            tokenizer=toknizer_path,
            state_dict=torch.load(
                model_weight_path, map_location="cpu", mmap=True, weights_only=True
            ),
        ).to(self.device)

    def _call_outeTTS(self):
        config_path = os.path.join(self.OuteTTS, "config.json")
        toknizer_path = os.path.join(self.OuteTTS, "tokenizer.json")
        model_weight_path = os.path.join(self.OuteTTS, "model.safetensors")

        for p in [config_path, toknizer_path, model_weight_path]:
            if not os.path.exists(p):
                logger.error(f"Path not Exist {p}")
                raise FileNotFoundError(f"Unable to locate path {p}")

        self.model = Outetts(
            tokenizer_path=toknizer_path,
            config=json.load(open(config_path)),
            safetensor_files=[model_weight_path],
        )

    def _call_audio_decoder(self):
        model_weights = os.path.join(self.OuteTTS, "decoder_model.pt")

        if not os.path.exists(model_weights):
            raise FileNotFoundError(f"Unable to locate path {model_weights}")

        self.model = load_decoder(model_weights, self.device)

    async def close(self):
        logger.info("Shutting down Translation Pipeline...")
