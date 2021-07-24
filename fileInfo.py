from datetime import datetime
from moviepy.editor import *
import os
import PIL.ExifTags
import re
import subprocess

image_ext = ".jpg", ".jpeg", ".png", ".gif"
video_ext = ".mov", ".avi", ".m4v", ".mp4"

def is_valid_path(path):
    """Checks if the given path exists"""
    return os.path.exists(path)

def get_media_files(path):
    """Returns the list of media files are in predefined folder"""
    return [file_name.lower() for file_name in os.listdir(path)
            if file_name.lower().endswith(image_ext + video_ext)]

def is_video_file(file_path):
    """Checks if the given file (with path) is a movie file"""
    return file_path.lower().endswith(video_ext)

def is_image_file(file_path):
    """Checks if the given file (with path) is an image"""
    return file_path.lower().endswith(image_ext)

def get_exif(file_path):
    result = {}
    if is_image_file(file_path):
        img = PIL.Image.open(file_path)
        result = getattr(img, '_getexif', lambda: {})()
        img.close()
    return result if result != None else {}

def get_video_metadata_creation_time(file_path):
    result =  "0000-00-00 00:00:00"
    try:
        cmd = ['ffprobe', '-print_format', 'json', '-show_format', file_path]
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err =  p.communicate()
        out = json.loads(out.decode('utf-8'))
        result = out['format']['tags']['creation_time']
    except (FileNotFoundError, KeyError) as e:
        #it ffbpobe.exe or the keys are not availale
        pass
    return result

def get_date_taken_from_file_name(file_name):
    result = -1
    match = re.search(r'\d{8}_\d{6}', file_name)
    if match:
        try:
            date = datetime.strptime(match.group(), '%Y%m%d_%H%M%S')
            result = date
        except ValueError as ve:
            pass
    return result

def get_date_taken_from_path(file_path, file_name):
    date_taken = get_date_taken_from_file_name(file_name)
    if date_taken == -1:
        date_taken = os.path.getctime(file_path)
        date_taken = datetime.fromtimestamp(date_taken)
    return date_taken

def get_formed_date_taken(file_path, file_name, date_value, zero_value, date_format):
    if date_value != zero_value:
        date_taken = datetime.strptime(date_value, date_format)
    else:
        date_taken = get_date_taken_from_path(file_path, file_name)
    return date_taken

def get_date_taken(file_path, file_name):
    date_taken = 0
    if is_image_file(file_path):
        exif_info = get_exif(file_path)
        date_taken = exif_info.get(36867, "0000:00:00 00:00:00")
        date_taken = get_formed_date_taken(file_path, file_name, date_taken,
                "0000:00:00 00:00:00", "%Y:%m:%d %H:%M:%S")
    elif is_video_file(file_path):
        date_taken = get_video_metadata_creation_time(file_path)
        date_taken = get_formed_date_taken(file_path, file_name, date_taken,
                "0000-00-00 00:00:00", "%Y-%m-%d %H:%M:%S")
    date_taken = date_taken.strftime('%Y%m%d%H%M%S')
    return date_taken

def get_orientation(file_path):
    exif_info = get_exif(file_path)
    return exif_info.get(274, 1)

def get_duration(file_path, file_name):
    result = 0
    if is_video_file(file_name):
        clip = VideoFileClip(file_path)
        result = clip.duration
    return result

def get_file_info(file_path, file_name):
    """get useful exif info of the file"""
    result = {}
    result['size'] = get_size(file_path)
    result['date_taken'] = get_date_taken(file_path, file_name)
    result['orient'] = get_orientation(file_path)
    result['duration'] = get_duration(file_path, file_name)
    return result

def get_size(file_path):
    """Returns the size of the given file in MB"""
    precision = 2
    sizes = ((1024*1024, "MB"), (1024, "Kb"), (2, "bytes"), (1, "byte"))
    if not is_valid_path(file_path):
        return '{}{}'.format(0, 'MB')
    size_in_bytes = os.path.getsize(file_path)
    for min_size, abbrev in sizes:
        if size_in_bytes >= min_size:
            return '{} {}'.format(
                    round(size_in_bytes / min_size, precision),
                    abbrev)
