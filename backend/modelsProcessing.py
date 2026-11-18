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

        self.model = None

    async def create_task(
        self,
        input_audio_path: str = None,
        project_id: int = None,
        project_name: str = None,
    ):

        if not os.path.exists(input_audio_path):
            logger.error(f"Unable to locate the input path: {input_audio_path}")
            return None

        project_dir = os.path.join(self.app_data_dir, "projects", project_name)
        os.makedirs(project_dir, exist_ok=True)

        task_id = str(uuid.uuid4())

        task = asyncio.create_task(
            self._run_pipeline(task_id, input_audio_path, project_id, project_dir)
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
        self,
        task_id: str,
        input_audio_path: str,
        project_id: int = None,
        project_dir: str = None,
        source_lang_token: str = "hin_Deva",
        target_lang_token: str = "eng_Latn",
    ):

        if self.ht == "p":
            logger.info(
                "Performance model integration is not supported yet. Falling back to the efficient model."
            )

        if self.ht not in ("e", "p"):
            logger.error(f"Invalid Hardware configuration! {self.ht}")
            raise ValueError(f"Invalid Hardware configuration! {self.ht}")

        try:

            # Speech-to-text generation

            self.translation_tasks[task_id]["current_working_task"] = "Speech-to-Text"
            self.translation_tasks[task_id]["status"] = "Loading STT Model..."
            self._call_whisper_small()
            logger.info(
                f"Whisper model loaded successfully on '{self.device.type}' and is ready for inference."
            )

            self.translation_tasks[task_id]["status"] = "Extracting Transcript..."
            transcript_saved_location = save_transcript(
                script=self.model(audio_path=input_audio_path, device=self.device),
                save_dir=project_dir,
            )
            self._clear_model_space()

            if not transcript_saved_location:
                logger.error(
                    f"Unable to save the transcipt in project dir {project_dir}"
                )  # Stop task execution; no further processing will be performed.

                self.translation_tasks[task_id]["status"] = "failed"
                self.translation_tasks[task_id][
                    "error"
                ] = "Unable to save transcription file."
            logger.info(f"Transcript save in {project_dir}")

            # updating database for transcript
            is_transcript_location_update = add_sql_data(
                table_name="projects",
                update=True,
                row_id=project_id,
                data={"stt_output": transcript_saved_location},
            )
            if not is_transcript_location_update:
                logger.warning(
                    "Failed to update transcription location in the database."
                )
            logger.info("Transcription location successfully saved to the database.")

            # Machine Translation

            self.translation_tasks[task_id][
                "current_working_task"
            ] = "Machine-Translaton"
            self.translation_tasks[task_id]["status"] = "Loading MT Model..."
            self._call_meta_nllb()
            logger.info(
                f"Meta-Nllb model loaded successfully on '{self.device.type}' and is ready for inference."
            )

            self.translation_tasks[task_id]["status"] = "Translating Transcript..."
            translation_saved_location = save_translation(
                translation=self.model(
                    source_txt=transcript_saved_location,
                    source_lang_token=source_lang_token,
                    target_lang_token=target_lang_token,
                    device=self.device,
                ),
                save_dir=project_dir,
            )
            self._clear_model_space()

            if not translation_saved_location:
                logger.error(
                    f"Unable to save the translation in project dir {project_dir}"
                )
                self.translation_tasks[task_id]["status"] = "failed"
                self.translation_tasks[task_id][
                    "error"
                ] = "Unable to save translation file."
            logger.info(f"Translation save in {project_dir}")

            # updating database for translation
            is_translation_location_update = add_sql_data(
                table_name="projects",
                update=True,
                row_id=project_id,
                data={"trans_output": translation_saved_location},
            )
            if not is_translation_location_update:
                logger.warning("Failed to update Translation location in the database.")
            logger.info("Translation location successfully saved to the database.")

            # Text-to-speech generation

            self.translation_tasks[task_id]["current_working_task"] = "Text-to-Speech"
            self.translation_tasks[task_id]["status"] = "Loading TTS Model..."
            self._call_outeTTS()
            logger.info(
                f"OuteTTS loaded successfully on '{self.device.type}' and is ready for inference."
            )

            self.translation_tasks[task_id]["status"] = "Generating speech codes..."
            speech_codes = self.model(
                script_path=translation_saved_location  # Need to pass Speaker
            )
            self._clear_model_space()
            logger.info("Audio code generated successfully!")

            self.translation_tasks[task_id][
                "current_working_task"
            ] = "Speech Generation"
            self.translation_tasks[task_id][
                "status"
            ] = "Loading audio decoding Model..."
            self._call_audio_decoder()
            logger.info(
                f"Audio decoder loaded successfully on '{self.device.type}' and is ready for inference."
            )

            self.translation_tasks[task_id]["status"] = "Speech generation..."
            audio_saved_location = save_wav(
                path=project_dir,
                audio=self.model(torch.tensor([speech_codes], device=self.device)),
            )
            self._clear_model_space()

            if audio_saved_location:

                is_audio_location_update = add_sql_data(
                    table_name="projects",
                    update=True,
                    row_id=project_id,
                    data={
                        "tts_output": translation_saved_location,
                        "final_output": translation_saved_location,
                    },
                )
                if not is_audio_location_update:
                    logger.warning("Failed to update Audio location in the database.")
                logger.info("Audio location successfully saved to the database.")

            logger.info("Audio generated successfully!")
            self.translation_tasks[task_id]["status"] = "Completed"
            self.translation_tasks[task_id]["current_working_task"] = "Done"

        except Exception as sttError:
            logger.exception(sttError)
            self.translation_tasks[task_id]["status"] = "failed"
            self.translation_tasks[task_id]["error"] = str(sttError)
            self._clear_model_space()

    def _clear_model_space(self):

        if self.device.type == "cuda":
            torch.cuda.empty_cache()

        del self.model
        self.model = None
        gc.collect()

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
