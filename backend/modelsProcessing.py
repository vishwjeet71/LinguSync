import json, uuid, os, asyncio
import logging, torch
from typing import Literal

from backend.models.stt.whisperSmall import WhisperSmall
from backend.models.stt.whisperSmallProcessing import save_transcript

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

    async def create_task(self, input_audio_path: str = None, project_dir: str = None):

        if not os.path.exists(input_audio_path):
            logger.error(f"Unable to locate the input path: {input_audio_path}")
            return None

        task_id = str(uuid.uuid4())

        task = asyncio.create_task(
            self._run_pipeline(task_id, input_audio_path, project_dir)
        )

        task_details = {
            "id": task_id,
            "hardware": self.ht,
            "current_working_task": None,  # stt, mt, tts, done
            "status": "idel",
            "task": task,
            "error": None,
        }

        self.translation_tasks[task_id] = task_details

        return task_id

    async def _run_pipeline(
        self, task_id: str, input_audio_path: str, project_dir: str = None
    ):

        if self.ht == "p":
            logger.info(
                "Performance model integration is not supported yet. Falling back to the efficient model."
            )

        if self.ht not in ("e", "p"):
            logger.error(f"Invalid Hardware configuration! {self.ht}")
            raise ValueError(f"Invalid Hardware configuration! {self.ht}")

        self.translation_tasks[task_id]["current_working_task"] = "stt"

        try:

            self.translation_tasks[task_id]["status"] = "Extracting Transcript..."
            model = self._call_whisper_small()
            stt_status = save_transcript(
                script=model(audio_path=input_audio_path, device=self.device),
                save_dir=project_dir,
            )

            del model

            if not stt_status:
                logger.warning(
                    f"Unable to save the transcipt in project dir {project_dir}"
                )  # Stop task execution; no further processing will be performed.

                self.translation_tasks[task_id]["status"] = "failed"
                self.translation_tasks[task_id][
                    "error"
                ] = "Unable to save transcription file."

            logger.info(f"Transcript save in {project_dir}")

        except Exception as sttError:
            self.translation_tasks[task_id]["status"] = "failed"
            self.translation_tasks[task_id]["error"] = sttError

    async def cancle_task(self, task_id: str):
        logger.warning("Task cancellation functionality has not been implemented yet.")
        return None

    def get_task_details(self, task_id):
        return self.translation_tasks.get(task_id)

    def _call_whisper_small(self):

        config_path = os.path.join(self.whisper_small_dir, "config.json")
        toknizer_path = os.path.join(self.whisper_small_dir, "tokenizer.json")
        model_weight_path = os.path.join(self.whisper_small_dir, "model.safetensors")

        for p in [config_path, toknizer_path, model_weight_path]:
            if not os.path.exists(p):
                logger.error(f"Path not Exist {p}")
                raise FileNotFoundError(f"Unable to locate path {p}")

        return WhisperSmall(
            config=json.load(open(config_path)),
            tokenizer=toknizer_path,
            safetensor_files=[model_weight_path],
        ).to(self.device)

    async def close(self):
        logger.info("Shutting down Translation Pipeline...")
