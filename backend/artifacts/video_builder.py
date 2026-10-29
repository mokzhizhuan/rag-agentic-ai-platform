"""Safe bounded still-image-to-MP4 renderer. Not generative video or arbitrary FFmpeg commands."""
import io
import os
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageOps

class VideoBuildError(ValueError):
    pass

ALLOWED_DURATIONS = {'video_clip': {5, 8, 10, 15}, 'video_reel': {30, 60}}


def build_video(images, mode, duration):
    """Render a 540p silent MP4 from uploaded/generated image bytes with slow zoom motion."""
    if mode not in ALLOWED_DURATIONS or duration not in ALLOWED_DURATIONS[mode]:
        raise VideoBuildError('Unsupported video mode/duration combination.')
    if not 1 <= len(images) <= 3:
        raise VideoBuildError('Please provide between 1 and 3 images.')
    with tempfile.TemporaryDirectory(prefix='rag-video-') as folder:
        root = Path(folder)
        sources=[]
        for idx, raw in enumerate(images):
            if len(raw)>8*1024*1024:
                raise VideoBuildError('Each reference image must be <= 8 MB.')
            try:
                with Image.open(io.BytesIO(raw)) as original:
                    original.verify()
                with Image.open(io.BytesIO(raw)) as original:
                    if original.width*original.height>24_000_000:
                        raise VideoBuildError('Reference image resolution is too large.')
                    rgb=ImageOps.exif_transpose(original).convert('RGB')
                    canvas=ImageOps.pad(rgb,(960,540),color=(0,0,0),method=Image.Resampling.LANCZOS)
                    path=root / f'input-{idx}.png'
                    canvas.save(path,format='PNG')
                    sources.append(path)
            except VideoBuildError:
                raise
            except (OSError,ValueError) as exc:
                raise VideoBuildError('A reference image could not be decoded.') from exc
        segments=[]
        for index, source in enumerate(sources):
            duration_segment = duration // len(sources) + (1 if index < duration % len(sources) else 0)
            dest=root / f'segment-{index}.mp4'
            # Apply gentle center zoom. No untrusted FFmpeg parameters originate from requests.
            filter_chain="scale=1024:576,zoompan=z='min(zoom+0.00045,1.065)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=960x540:fps=15,format=yuv420p"
            cmd=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-loop','1','-framerate','15','-i',str(source),'-t',str(duration_segment),'-vf',filter_chain,'-an','-c:v','libx264','-preset','ultrafast','-crf','31','-movflags','+faststart',str(dest)]
            try:
                result=subprocess.run(cmd,timeout=max(75,duration_segment*5),capture_output=True,text=True,check=False)
            except (OSError,subprocess.TimeoutExpired) as exc:
                raise VideoBuildError('FFmpeg is missing or video rendering timed out. Check the Docker image.') from exc
            if result.returncode!=0:
                raise VideoBuildError('FFmpeg could not render the video; check that libx264 is installed.')
            segments.append(dest)
        listfile=root/'segments.txt'
        listfile.write_text(''.join(f"file '{str(item)}'\n" for item in segments),encoding='utf-8')
        output=root/'result.mp4'
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-f','concat','-safe','0','-i',str(listfile),'-c','copy','-movflags','+faststart',str(output)]
        try:
            result=subprocess.run(cmd,timeout=30,capture_output=True,text=True,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise VideoBuildError('FFmpeg could not combine video segments.') from exc
        if result.returncode!=0 or not output.exists():
            raise VideoBuildError('FFmpeg video assembly failed.')
        size=output.stat().st_size
        if size > 15*1024*1024:
            raise VideoBuildError('Video is larger than the configured artifact limit (15 MiB).')
        return output.read_bytes()
