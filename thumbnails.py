from PIL import Image
from fileInfo import *
import os
from moviepy.editor import *
from io import BytesIO

thumb_width = 500;
thumb_prefix = "tbnl_" 
thumb_ext = ".jpg"

def calculate_size(image):
    width, height = image.size
    if width < height:
        return thumb_width, int(height * thumb_width / width)
    else:
        return int(width * thumb_width / height), thumb_width

def resize_and_save_image(image):
    image.thumbnail(calculate_size(image), Image.ANTIALIAS)
    output = BytesIO()
    image.save(output, 'JPEG')
    #go back to the begining of the file
    output.seek(0)
    return output

def save_image_thumbnail(original_file_path):
    im = Image.open(original_file_path)
    #for png transparency:
    im = im.convert('RGB')
    #rotation according to the exif orientation data
    orientation = get_orientation(original_file_path)
    if orientation == 3:
        im = im.rotate(180)
    if orientation == 6:
        im = im.rotate(270, expand = True)
    if orientation == 8:
        im = im.rotate(90, expand = True)
    return resize_and_save_image(im)

def save_video_thumbnail(original_file_path):
    """Saves thumbnail of the given video under the given name"""
    clip = VideoFileClip(original_file_path)
    im = Image.fromarray(clip.get_frame(0))
    return resize_and_save_image(im)
    
def get_thumbnail_name(file_name):
    orig_name, orig_ext= os.path.splitext(file_name.lower())
    thumbnail_name = thumb_prefix + orig_name + thumb_ext
    return thumbnail_name

def generate_thubnail(full_path, file_name):
    orig_name, orig_ext= os.path.splitext(file_name.lower())
    
    try:
        if orig_ext in image_ext:
            return save_image_thumbnail(full_path)
        elif orig_ext in video_ext:
            return save_video_thumbnail(full_path)
    except Exception as e:
        print(e)
        print("no thumbnail for file: %s" %full_path)