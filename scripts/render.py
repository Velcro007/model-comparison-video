#!/usr/bin/env python3
"""Portable Offloop two-to-four-model comparison renderer. Python 3.10+, Pillow, FFmpeg."""
import argparse
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent


def run(args):
    subprocess.run([str(x) for x in args], check=True)


def executable(value, default):
    found = shutil.which(value or default)
    if not found:
        raise ValueError(f"Cannot find {value or default}. Install FFmpeg and add its bin folder to PATH.")
    return found


def metadata(probe, path):
    import imageio_ffmpeg
    reader = imageio_ffmpeg.read_frames(str(path))
    info = next(reader)
    reader.close()
    return {'streams': [{'codec_type': 'video'}], 'format': {'duration': info['duration']}}


def font(size):
    face = ImageFont.truetype(str(ROOT / 'assets/InterVariable.ttf'), max(8, round(size)))
    try:
        face.set_variation_by_axes([14, 700])
    except (OSError, ValueError):
        pass
    return face


def make_overlay(ffmpeg, cfg, models, target):
    size, fps = cfg['panel_size'], cfg['fps']
    k = size / 1080
    n = lambda v: round(v * k)
    cols, rows = (2, 2) if len(models) == 4 else (len(models), 1)
    canvas = Image.new('RGBA', (size * cols, size * rows))
    draw = ImageDraw.Draw(canvas)
    label, value_font = font(21 * k), font(38 * k)
    for i, model in enumerate(models):
        ox, oy = (i % cols) * size, (i // cols) * size
        title = font(44 * k)
        while draw.textlength(model['name'], font=title) > n(850) and title.size > 10:
            title = font(title.size - 1)
        width = math.ceil(draw.textlength(model['name'], font=title)) + n(110)
        x = ox + (size - width) // 2
        draw.rounded_rectangle((x, oy+n(14), x+width, oy+n(88)), radius=n(6), fill='white')
        logo = Image.open(model['_logo']).convert('RGBA')
        logo.thumbnail((n(54), n(54)), Image.Resampling.LANCZOS)
        canvas.alpha_composite(logo, (x+n(15)+(n(54)-logo.width)//2, oy+n(24)+(n(54)-logo.height)//2))
        draw.text((x+n(84), oy+n(51)), model['name'], font=title, fill='#111111', anchor='lm')
        for j, text in enumerate(['TIME', 'COST']):
            left = ox+n(24)+j*(size//2)
            draw.text((left, oy+n(1025)), text, font=label, fill='#20301a', anchor='ls',
                      stroke_width=max(1,n(1)), stroke_fill='#f7f3e7')
            draw.rectangle((left, oy+n(1042), left+n(491), oy+n(1060)), fill=(20,26,15,80))
    mark = Image.open(ROOT/'assets/offloop.png').convert('RGBA').resize((n(46),n(46)), Image.Resampling.LANCZOS)
    canvas.alpha_composite(mark, (n(14),n(20)))
    for col in range(1, cols):
        draw.rectangle((size*col-1,0,size*col,size*rows-1), fill='white')
    if rows == 2:
        draw.rectangle((0,size-1,size*cols-1,size), fill='white')
    proc = subprocess.Popen([ffmpeg,'-v','error','-y','-f','rawvideo','-pix_fmt','rgba',
        '-s',f'{size*cols}x{size*rows}','-r',str(fps),'-i','pipe:0','-an','-c:v','qtrle',
        '-pix_fmt','argb',str(target)], stdin=subprocess.PIPE)
    try:
        for frame in range(cfg['_frames']):
            p = min(1, frame / fps / cfg['animation_seconds'])
            image = canvas.copy()
            d = ImageDraw.Draw(image)
            for i, model in enumerate(models):
                ox, oy = (i % cols)*size, (i // cols)*size
                sec = round(model['time_seconds']*p)
                values = [(f'{sec//60}m {sec%60:02d}s', model['time_seconds']/cfg['time_scale_seconds']),
                          ('$'+format(model['cost_usd']*p, f'.{model.get("cost_decimals",3)}f'),
                           model['cost_usd']/cfg['cost_scale_usd'])]
                for j, (text, fraction) in enumerate(values):
                    x = ox+n(24)+j*(size//2)
                    d.text((x+n(492),oy+n(1025)), text, font=value_font, fill='#172011', anchor='rs',
                           stroke_width=max(1,n(1)), stroke_fill='#f7f3e7')
                    width = round(n(492)*min(1,fraction)*p)
                    if width > 0:
                        d.rectangle((x,oy+n(1042),x+width-1,oy+n(1060)), fill='#D4FD4D')
                        if j == 0:
                            for xx in range(x+n(12),x+width,max(1,n(15))):
                                d.rectangle((xx,oy+n(1042),min(xx+max(1,n(2)),x+width-1),oy+n(1060)), fill='#97BC39')
            proc.stdin.write(image.tobytes())
    finally:
        proc.stdin.close()
        result = proc.wait()
    if result:
        raise RuntimeError('Animated overlay encoding failed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default=str(ROOT/'config.json'))
    parser.add_argument('--check', action='store_true', help='Validate inputs without rendering.')
    args = parser.parse_args()
    config_path = Path(args.config).resolve()
    cfg = json.loads(config_path.read_text(encoding='utf-8'))
    resolve = lambda p: (config_path.parent / p).resolve()
    import imageio_ffmpeg
    ffmpeg = executable(cfg.get('ffmpeg') or imageio_ffmpeg.get_ffmpeg_exe(), 'ffmpeg')
    ffprobe = ffmpeg
    models = cfg['models']
    if len(models) not in (2,3,4):
        raise ValueError('Supply 2, 3 or 4 models.')
    for key in ['fps','duration_seconds','speed','animation_seconds','time_scale_seconds','cost_scale_usd']:
        if not isinstance(cfg[key], (float,int)) or not math.isfinite(cfg[key]) or cfg[key] <= 0:
            raise ValueError(f'{key} must be a positive finite number.')
    if not isinstance(cfg['fps'], int) or not isinstance(cfg['panel_size'], int) or cfg['panel_size'] < 240 or cfg['panel_size'] % 2:
        raise ValueError('fps must be an integer; panel_size must be even and at least 240.')
    cfg['_frames'] = round(cfg['fps']*cfg['duration_seconds'])
    if cfg['_frames'] < 2 or cfg['animation_seconds'] > (cfg['_frames']-1)/cfg['fps']:
        raise ValueError('Animation must finish before the last output frame.')
    for model in models:
        for key in ['time_seconds','cost_usd','trim_start_seconds']:
            value = model.get(key,0)
            if not isinstance(value,(float,int)) or not math.isfinite(value) or value < 0:
                raise ValueError(f'{model["name"]}: {key} must be finite and nonnegative.')
        if model['time_seconds'] > cfg['time_scale_seconds'] or model['cost_usd'] > cfg['cost_scale_usd']:
            raise ValueError('Increase the shared bar scales to contain all supplied totals.')
        if model.get('fit','crop') not in ('crop','contain'):
            raise ValueError('fit must be crop or contain.')
        model['_path'] = resolve(model['video'])
        model['_logo'] = resolve(model['logo'])
        if not model['_path'].is_file() or not model['_logo'].is_file():
            raise ValueError(f'Missing video or logo for {model["name"]}: {model["_path"]}')
        meta = metadata(ffprobe,model['_path'])
        if not any(s['codec_type']=='video' for s in meta['streams']):
            raise ValueError(f'No video stream: {model["_path"]}')
        model['_duration'] = float(meta['format']['duration'])
        end = model.get('trim_end_seconds',model['_duration'])
        if not model.get('trim_start_seconds',0) < end <= model['_duration']:
            raise ValueError(f'Invalid source trim range: {model["name"]}')
    music = resolve(cfg['music']) if cfg.get('music') else None
    if music and not music.is_file():
        raise ValueError(f'Missing music: {music}')
    print('Validated videos, logos, metrics, trims, and tools.', flush=True)
    if args.check:
        return
    output = resolve(cfg.get('output','output/offloop-comparison.mp4'))
    if output in [m['_path'] for m in models]:
        raise ValueError('Output must not overwrite an input video.')
    output.parent.mkdir(parents=True,exist_ok=True)
    size, fps = cfg['panel_size'],cfg['fps']
    duration = cfg['_frames']/fps
    with tempfile.TemporaryDirectory(prefix='offloop-') as temp:
        work = Path(temp)
        for i, model in enumerate(models):
            print(f'Preparing panel {i+1}/{len(models)}: {model["name"]}', flush=True)
            start = model.get('trim_start_seconds',0)
            end = min(model.get('trim_end_seconds',model['_duration']),start+duration*cfg['speed'])
            bg = model.get('background')
            if not bg:
                still = work/f'color-{i}.png'
                run([ffmpeg,'-v','error','-y','-ss',str(start),'-i',model['_path'],
                     '-frames:v','1','-update','1',still])
                rgb = Image.open(still).convert('RGB').getpixel((10,10))
                bg = '0x'+''.join(f'{c:02x}' for c in rgb)
            inner = round(size*960/1080)//2*2
            if model.get('fit','crop') == 'contain':
                fit = f'scale={inner}:{inner}:force_original_aspect_ratio=decrease,pad={inner}:{inner}:(ow-iw)/2:(oh-ih)/2:color={bg}'
            else:
                fit = f"crop='min(iw,ih)':'min(iw,ih)',scale={inner}:{inner}:flags=lanczos"
            vf = f'setpts=(PTS-STARTPTS)/{cfg["speed"]},fps={fps},{fit},pad={size}:{size}:(ow-iw)/2:(oh-ih)/2:color={bg},setsar=1'
            run([ffmpeg,'-v','error','-y','-ss',str(start),'-t',str(end-start),'-i',model['_path'],
                 '-vf',vf,'-an','-c:v','libx264','-preset','fast','-crf','18','-threads','2',
                 '-pix_fmt','yuv420p',work/f'panel-{i}.mp4'])
        print('Rendering animated titles, time, and cost bars.', flush=True)
        make_overlay(ffmpeg,cfg,models,work/'overlay.mov')
        command = [ffmpeg,'-v','error','-y','-filter_complex_threads','1']
        for i in range(len(models)):
            command += ['-stream_loop','-1','-i',str(work/f'panel-{i}.mp4')]
        command += ['-i',str(work/'overlay.mov')]
        if music:
            command += ['-stream_loop','-1','-i',str(music)]
        count = len(models)
        if count == 4:
            grid = '[0:v][1:v]hstack[top];[2:v][3:v]hstack[bottom];[top][bottom]vstack[grid]'
        else:
            grid = ''.join(f'[{i}:v]' for i in range(count)) + f'hstack=inputs={count}[grid]'
        filters = grid + f';[grid][{count}:v]overlay=0:0:format=auto,format=yuv420p[out]'

        if music:
            fade = min(.25,duration/4)
            filters += f';[{count+1}:a]atrim=duration={duration},asetpts=PTS-STARTPTS,loudnorm=I=-14:TP=-1.1:LRA=7,afade=t=in:d=0.015,afade=t=out:st={duration-fade}:d={fade}[audio]'
        command += ['-filter_complex',filters,'-map','[out]']
        command += ['-map','[audio]','-c:a','aac','-b:a','256k','-ar','48000'] if music else ['-an']
        command += ['-t',str(duration),'-r',str(fps),'-c:v','libx264','-preset','fast','-crf','18',
                    '-threads','4','-pix_fmt','yuv420p','-movflags','+faststart',str(output)]
        run(command)
    print(f'Created: {output}', flush=True)


if __name__ == '__main__':
    try:
        main()
    except (ValueError,subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
