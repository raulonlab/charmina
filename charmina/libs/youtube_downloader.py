# Resources:
# Download youtube video: https://dev.to/stokry/download-youtube-video-to-mp3-with-python-26p
# video attributes: title, description, views, rating, length, keywords, thumbnail_url, video_id, age_restricted, channel_id, channel_url, watch_url, captions, publish_date, start_time, end_time, category, tags

import json
import random
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from time import sleep
import glob
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pytubefix import YouTube, Playlist, Channel, extract
import music_tag
from typing import List, Optional, Union, Tuple
import os
import logging
from charmina.libs.event_emitter import EventEmitter
from charmina.config import Config


_RUN_TASKS_LIMIT = 1_000  # Maximum number of tasks to run in a single call to run()


class YoutubeDownloader(EventEmitter):
    video_urls: list = []
    downloaded_urls: set = set()
    config: Config = Optional[Config]

    def __init__(self, source_urls: List[str] = [], config: Config = None):
        super().__init__()

        if config:
            self.config = config
        else:
            self.config = Config.instance()

        self.add_sources(source_urls)

        video_urls_str = "\n".join(self.video_urls)

    def add_sources(self, source_urls: Union[str, List]):
        if source_urls is str:
            source_urls = [source_urls]

        for video_url in source_urls:
            if "/watch?v=" in video_url:
                self.video_urls.append(video_url)
            elif "/playlist?list=" in video_url:
                playlist = Playlist(video_url)
                if (self.config.YOUTUBE_MAXIMUM_EPISODE_COUNT) > 0:
                    self.video_urls.extend(
                        playlist.video_urls[
                            0 : min(
                                self.config.YOUTUBE_MAXIMUM_EPISODE_COUNT,
                                len(playlist.video_urls),
                            )
                        ]
                    )
                else:
                    self.video_urls.extend(playlist.video_urls)
            elif "/channel/" in video_url or "/@" in video_url:
                channel = Channel(video_url)
                if (self.config.YOUTUBE_MAXIMUM_EPISODE_COUNT) > 0:
                    # Iterate through the playlist
                    for index, video_aux in enumerate(channel.videos, start=1):
                        video_url = video_aux.watch_url
                        # print("channel video_url: ", video_url)
                        self.video_urls.append(video_url)

                        if (
                            len(self.video_urls)
                            > self.config.YOUTUBE_MAXIMUM_EPISODE_COUNT - 1
                        ):
                            break

                    # self.video_urls.extend(
                    #     channel.video_urls[
                    #         0 : min(
                    #             self.config.YOUTUBE_MAXIMUM_EPISODE_COUNT,
                    #             len(channel.video_urls),
                    #         )
                    #     ]
                    # )
                    # for video_url in channel.videos_url .video_urls:
                    #     print("cannel video_url: ", video_url)
                    #     self.video_urls.append(video_url)

                    #     if len(self.video_urls) > self.config.YOUTUBE_MAXIMUM_EPISODE_COUNT - 1:
                    #         break
                else:
                    self.video_urls.extend(channel.video_urls)

    def run(
        self, output_path=".", limit: int = _RUN_TASKS_LIMIT
    ) -> Tuple[List[str], List[any]]:
        logging.debug("Running youtube downloader...")

        # Find downloaded video ids to skip them
        if self.config.YOUTUBE_DOWNLOAD_TYPE == "audio":
            downloaded_video_ids = self.find_downloaded_audio_video_ids(output_path)
        else:
            downloaded_video_ids = self.find_downloaded_caption_video_ids(output_path)

        download_arguments = []
        for video_url in self.video_urls:
            if extract.video_id(video_url) in downloaded_video_ids:
                logging.debug(f"Video '{video_url}' already downloaded. Skipping.")
                continue

            download_arguments.append(
                {"url": str(video_url), "output_path": output_path}
            )

        # Return if no video to download
        if len(download_arguments) == 0:
            logging.debug("No videos to download")
            return [], []

        # Limit number of tasks to run
        if not limit or not 0 < limit < _RUN_TASKS_LIMIT:
            limit = _RUN_TASKS_LIMIT
        if len(download_arguments) > limit:
            logging.warning(
                f"Number of videos to download cut to limit {limit}  (out of {len(download_arguments)})"
            )
            download_arguments = download_arguments[:limit]

        logging.debug(f"Start processing {len(download_arguments)} urls...")

        # Emit start event (show progress bar in UI)
        self.emit("start", len(download_arguments))

        results = []
        errors = []
        max_workers = 1  # Maximum 1 worker (1 download at a time)
        with ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="YoutubeDownloader"
        ) as executor:
            response_futures = [
                executor.submit(
                    (
                        self.download_audio
                        if self.config.YOUTUBE_DOWNLOAD_TYPE == "audio"
                        else self.download_caption
                    ),
                    download_argument,
                )
                for download_argument in download_arguments
            ]

            for response_future in as_completed(response_futures):
                try:
                    response = response_future.result()
                    if response:
                        results.append(response)
                        self.emit("write", str(response))
                    else:
                        self.emit("write", "")
                except Exception as err:
                    errors.append(err)
                    self.emit("write", str(err), is_error=True)
                    continue
                finally:
                    self.emit("update")

        self.emit("close")

        return results, errors

    def download_audio(self, input_arguments) -> Union[str, None]:
        """Download audio from YouTube video url."""

        url: str = input_arguments["url"]
        output_path: str = input_arguments["output_path"]

        wait_seconds = random.randint(
            self.config.YOUTUBE_SLEEP_SECONDS_BETWEEN_DOWNLOADS,
            2 * self.config.YOUTUBE_SLEEP_SECONDS_BETWEEN_DOWNLOADS,
        )
        logging.debug(
            f"Start downloading video url {url}  ...waiting {wait_seconds} seconds"
        )
        sleep(wait_seconds)

        try:
            yt = YouTube(url)
        except Exception as err:
            logging.error(
                f"✘ Error getting video '{url}' from YouTube. Skipping download.",
                exc_info=err,
            )
            return None

        channel_title = yt.author
        video_title = yt.title
        try:
            publish_date = yt.publish_date
        except Exception as err:
            logging.warning(
                f"Error getting publish date of '{video_title}' from channel '{channel_title}' (url: {url})",
                exc_info=err,
            )
            publish_date = None

        # Audio output file
        audio_output_filename = f"{video_title}.mp3"
        if self.config.YOUTUBE_ADD_DATE_PREFIX is True and publish_date is not None:
            if isinstance(publish_date, datetime):
                date_str = publish_date.strftime("%Y-%m-%d")
            elif isinstance(publish_date, str) and len(publish_date) > 9:
                date_str = publish_date[:10]
            else:
                date_str = None
                logging.warning(
                    f"Video '{video_title}' has invalid publish date. Skipping date prefix."
                )

            if date_str is not None:
                audio_output_filename = f"{date_str} {audio_output_filename}"
        elif publish_date is None:
            logging.warning(
                f"Video '{video_title}' has no publish date. Skipping date prefix."
            )

        # Slugify / fix titles
        if self.config.YOUTUBE_SLUGIFY_PATHS:
            audio_output_filename = self.slugify_string(audio_output_filename)
            channel_title = self.slugify_string(channel_title)
        else:
            audio_output_filename = audio_output_filename.replace(os.path.pathsep, "_")
            audio_output_filename = audio_output_filename.replace(os.path.sep, "_")
            channel_title = channel_title.replace(os.path.pathsep, "_")
            channel_title = channel_title.replace(os.path.sep, "_")

        # Output path
        if self.config.YOUTUBE_GROUP_BY_AUTHOR:
            output_path = str(Path(output_path, channel_title))

        audio_output_file_path = os.path.join(output_path, audio_output_filename)
        if os.path.exists(audio_output_file_path):
            logging.debug(
                f"Audio file '{audio_output_file_path}' already exists. Skipping download."
            )
            self.write_tags(audio_output_file_path, yt)

            return None

        # Extract audio from video
        audio_output_file_path = None
        try:
            logging.debug(
                f"Downloading audio of video '{video_title}' from channel '{channel_title}'..."
            )

            video = yt.streams.get_audio_only()
            audio_output_file_path = video.download(
                # mp3=False,  # mp3 == True, ignores filename and uses video title
                output_path=output_path,
                filename=audio_output_filename,
                filename_prefix=None,
                skip_existing=True,
                # timeout: Optional[int] = None,
                # max_retries: Optional[int] = 0
            )
        except Exception as err:
            logging.error(
                f"✘ Error downloading '{video_title}' from channel '{channel_title}' (url: {url})",
                exc_info=err,
            )
            traceback.print_exc()
            return None

        file_stats = os.stat(audio_output_file_path)
        if file_stats.st_size > 100000000:
            logging.warning(
                f"Size of audio file {file_stats.st_size / 1024}Mb exceeds maximum of 100Mb"
            )
            return None

        # Validate downloaded audio file
        if os.path.exists(audio_output_file_path):
            logging.debug(
                f"✔ Audio file '{audio_output_file_path}' downloaded successfully."
            )

            self.write_tags(audio_output_file_path, yt)
            return audio_output_file_path
        else:
            logging.error(
                f"✘ Unable to download audio of '{video_title}' from channel '{channel_title}' (url: {url}). Audio output file path doesn't exist: {audio_output_file_path} "
            )
            return None

    def download_caption(self, input_arguments) -> Union[str, None]:
        """Download caption from YouTube video url."""

        url: str = input_arguments["url"]
        output_path: str = input_arguments["output_path"]

        wait_seconds = random.randint(
            self.config.YOUTUBE_SLEEP_SECONDS_BETWEEN_DOWNLOADS,
            2 * self.config.YOUTUBE_SLEEP_SECONDS_BETWEEN_DOWNLOADS,
        )
        logging.debug(
            f"Start downloading caption of video url {url}  ...waiting {wait_seconds} seconds"
        )
        sleep(wait_seconds)

        try:
            yt = YouTube(url)
        except Exception as err:
            logging.error(
                f"✘ Error getting video '{url}' from YouTube. Skipping download.",
                exc_info=err,
            )
            return None

        channel_title = yt.author
        video_title = yt.title
        try:
            publish_date = yt.publish_date
        except Exception as err:
            logging.warning(
                f"Error getting publish date of '{video_title}' from channel '{channel_title}' (url: {url})",
                exc_info=err,
            )
            publish_date = None

        # output file
        caption_output_filename = f"{video_title}.{yt.video_id}.caption"
        if self.config.YOUTUBE_ADD_DATE_PREFIX is True and publish_date is not None:
            if isinstance(publish_date, datetime):
                date_str = publish_date.strftime("%Y-%m-%d")
            elif isinstance(publish_date, str) and len(publish_date) > 9:
                date_str = publish_date[:10]
            else:
                date_str = None
                logging.warning(
                    f"Video '{video_title}' has invalid publish date. Skipping date prefix."
                )

            if date_str is not None:
                caption_output_filename = f"{date_str} {caption_output_filename}"
        elif publish_date is None:
            logging.warning(
                f"Video '{video_title}' has no publish date. Skipping date prefix."
            )

        # Slugify / fix titles
        if self.config.YOUTUBE_SLUGIFY_PATHS:
            caption_output_filename = self.slugify_string(caption_output_filename)
            channel_title = self.slugify_string(channel_title)
        else:
            caption_output_filename = caption_output_filename.replace(
                os.path.pathsep, "_"
            )
            caption_output_filename = caption_output_filename.replace(os.path.sep, "_")
            channel_title = channel_title.replace(os.path.pathsep, "_")
            channel_title = channel_title.replace(os.path.sep, "_")

        # Output path
        if self.config.YOUTUBE_GROUP_BY_AUTHOR:
            output_path = str(Path(output_path, channel_title))

        caption_output_file_path = os.path.join(output_path, caption_output_filename)
        if os.path.exists(caption_output_file_path):
            logging.debug(
                f"Caption file '{caption_output_file_path}' already exists. Skipping download."
            )

            return None

        # Download caption of video
        try:
            logging.debug(
                f"Downloading caption of video '{video_title}' from channel '{channel_title}'..."
            )

            try:
                caption = yt.captions["en"]
            except:
                caption = None
            if not caption:
                try:
                    caption = yt.captions["a.en"]
                except:
                    caption = None

            if not caption:
                logging.warning(
                    f"✘ No caption found for video '{video_title}' from channel '{channel_title}' (url: {url})"
                )
                return None

            caption.save_captions(caption_output_file_path)

        except Exception as err:
            logging.error(
                f"✘ Error downloading '{video_title}' from channel '{channel_title}' (url: {url})",
                exc_info=err,
            )
            traceback.print_exc()
            return None

        # Validate downloaded audio file
        if os.path.exists(caption_output_file_path):
            logging.debug(
                f"✔ Caption file '{caption_output_file_path}' downloaded successfully."
            )

            # self.write_tags(caption_output_file_path, yt)
            return caption_output_file_path
        else:
            logging.error(
                f"✘ Unable to download caption of '{video_title}' from channel '{channel_title}' (url: {url}). Caption output file path doesn't exist: {caption_output_file_path} "
            )
            return None

    @staticmethod
    def slugify_string(filename: str) -> str:
        filename = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore")
        filename = re.sub("[^\w\s\-\.]", "", filename.decode("ascii")).strip()
        filename = re.sub("[-\s]+", "-", filename)

        return filename

    @staticmethod
    def find_downloaded_audio_video_ids(directory_path: str) -> set:
        downloaded_video_ids = set()

        for filename in glob.iglob(
            os.path.join(directory_path, "./**/*.mp3"), recursive=True
        ):
            try:
                music_tag_file = music_tag.load_file(os.path.abspath(filename))
                video_url = str(music_tag_file["comment"])
                if video_url:
                    downloaded_video_ids.add(extract.video_id(video_url))
            except:
                continue

        return downloaded_video_ids

    @staticmethod
    def find_downloaded_caption_video_ids(directory_path: str) -> set:
        downloaded_video_ids = set()

        for filename in glob.iglob(
            os.path.join(directory_path, "./**/*.caption"), recursive=True
        ):
            try:
                filename_id_part = os.path.basename(filename).split(".")[-2]
                if len(filename_id_part) != 11:
                    continue

                downloaded_video_ids.add(filename_id_part)
            except:
                continue

        return downloaded_video_ids

    @staticmethod
    def write_tags(filepath: str, yt: YouTube) -> None:
        music_tag_file = None

        try:
            music_tag_file = music_tag.load_file(filepath)
        except:
            # Retry after 1 second
            sleep(1)
            try:
                music_tag_file = music_tag.load_file(filepath)
            except:
                logging.error(f"✘ Unable to write file tags in '{filepath}'")
                return

        # Sanatise publish date
        publish_date = yt.publish_date
        if isinstance(publish_date, datetime):
            publish_date_str = publish_date.strftime("%Y-%m-%d")
        else:
            publish_date_str = None

        # music_tag_file["title"] = yt.title
        # music_tag_file["album"] = yt.author
        # music_tag_file["author"] = yt.author
        music_tag_file["comment"] = json.dumps(
            {
                "author": yt.author,
                "title": yt.title,
                "album": yt.author,
                "source_id": yt.video_id,
                "source_type": "youtube",
                "publish_date": publish_date_str,
                "url": yt.watch_url,
                "description": yt.description,
                # "language": yt.language,
                "rating": yt.rating,
            }
        )

        music_tag_file.save()
