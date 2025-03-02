# Description: Mp3 transformer.

from faster_whisper import WhisperModel
import torch
from typing import ClassVar, Tuple
from charmina.config import Config
from charmina.libs.helpers import check_for_package, TimeTaken
from charmina.modules.dataclasses import TransformConfig

try:
    from whisper_mps import whisper as whispermps
except ImportError:
    pass


class Mp3Transformer:
    """Mp3 transformer.


    Args:
        file_path: Path to the file to load.
    """

    file_path: str
    model_name: str
    package: str
    device: ClassVar[str] = None
    compute_type: ClassVar[str] = None

    def __init__(
        self,
        file_path: str,
        transform_config: TransformConfig = TransformConfig(),
        model_name: str = None,
        package: str = None,
    ):
        """Initialize with file path."""
        self.file_path = file_path
        self.model_name = (
            model_name or Config.instance().WHISPER_TRANSCRIPTION_MODEL_NAME
        )
        self.package = package or Config.instance().WHISPER_PACKAGE_NAME

        if not self.model_name:
            raise ValueError("No transcription model name provided")

        if not self.package:
            raise ValueError("No transcription package name provided")

        if self.package == "whisper-mps" and not check_for_package("whisper_mps"):
            raise ImportError(
                "Whisper-MPS package not found. Please install it manually (poetry run pip install whisper-mps)"
            )

        # check for device and compute type if not provided
        if not self.device:
            self.device, self.compute_type = self.check_device()

        # print(f"Using {self.device} device for transcription")
        # print(f"Using {self.package} package for transcription")
        # print(f"Using {self.compute_type} compute type for transcription")

    def transform(self) -> str:
        """Transform Mp3 file path."""
        transcript = ""

        if self.package == "whisper-mps":
            # use whisper-mps package
            with TimeTaken("Transcribe audio"):
                result = whispermps.transcribe(self.file_path, model=self.model_name)
                transcript = str(result.get("text", "")).strip(" \n")

        # elif package == "transformers":
        #     # use transformers package
        #     # https://huggingface.co/docs/transformers/v4.39.3/en/main_classes/pipelines#transformers.AutomaticSpeechRecognitionPipeline
        #     pipe: AutomaticSpeechRecognitionPipeline = pipeline(
        #         "automatic-speech-recognition",
        #         model=model_name, # select checkpoint from https://huggingface.co/openai/whisper-large-v3#model-details
        #         torch_dtype=compute_type,
        #         device=device, # or mps for Mac devices
        #         model_kwargs={"attn_implementation": "flash_attention_2"} if is_flash_attn_2_available() else {"attn_implementation": "sdpa"},
        #     )

        #     with TimeTaken("Transcribe audio"):
        #         result = pipe(
        #             input_audio_file_path,
        #             chunk_length_s=30,  # 10?
        #             batch_size=4,
        #             return_timestamps=False,
        #     )
        #     transcript = str(result.get("text", "")).strip(" \n")

        else:
            # use faster-whisper package
            model = WhisperModel(
                self.model_name,
                device=self.device if self.device in ["cuda:0", "cpu"] else "auto",
                compute_type=self.compute_type,
                cpu_threads=4,
                num_workers=1,
            )

            segments, info = model.transcribe(
                self.file_path,
                beam_size=1 if self.model_name.startswith("distil-") else 5,
                language="en",
                without_timestamps=True,
                # num_workers=1,
                condition_on_previous_text=False,
            )

            with TimeTaken("Transcribe audio"):
                segments_str = "".join([segment.text for segment in segments])
                transcript = segments_str.strip(" \n")

        return transcript

    @staticmethod
    def check_device() -> Tuple[str, str]:
        """Check CUDA availability."""
        if torch.cuda.is_available() == 1:
            device = "cuda:0"
            compute_type = "float16"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            device = "mps"
            compute_type = "int8"
        else:
            device = "cpu"
            compute_type = "float32"

        return device, compute_type
