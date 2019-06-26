import boto3, botocore
import os, sys, hashlib
import PIL.Image, PIL.ExifTags
from datetime import datetime
import configparser
import threading

s3=boto3.resource('s3')
#s3=boto3.resource('s3')
base_bucket_name = "photos.pataky."
hash_file=".amazonUploader" #file contains albumname and file-hash pairs
hash_photos = "Photos"
hash_album = "Album"
image_ext = ".jpg", ".jpeg", ".png", ".gif"
video_ext = ".mov", ".avi", ".m4v", ".mp4"
hash_prefix = "sha256_"

def is_valid_path(path):
    """Checks if the given path exists"""
    return os.path.exists(path)

def get_media_files(path):
    """Returns the list of media files are in predefined folder"""
    return [file_name for file_name in os.listdir(path)
            if file_name.lower().endswith(image_ext + video_ext)]

def is_video_file(file_path):
    """Checks if the given file (with path) is a movie file"""
    return file_path.lower().endswith(video_ext)

def get_exif(file_path):
    result = {}
    if is_image_file(file_path):
        img = PIL.Image.open(file_path)
        result = getattr(img, '_getexif', lambda: {})()
        img.close()
    return result if result != None else {}

def is_image_file(file_path):
    """Checks if the given file (with path) is an image"""
    return file_path.lower().endswith(image_ext)

def get_file_info(file_path):
    """get useful exif info of the file"""
    exif_info = get_exif(file_path)
    result = {}
    date_taken = exif_info.get(36867, "0000:00:00 00:00:00")
    if date_taken != "0000:00:00 00:00:00":
        date_taken = datetime.strptime(date_taken, '%Y:%m:%d %H:%M:%S')
    else:
        date_taken = os.path.getctime(file_path)
        date_taken = datetime.fromtimestamp(date_taken)
    result['date_taken'] = date_taken.strftime('%Y-%m-%d %H:%M:%S')

    date_modif = exif_info.get(306, "0000:00:00 00:00:00")
    if date_modif != "0000:00:00 00:00:00":
        date_modif = datetime.strptime(date_modif, '%Y:%m:%d %H:%M:%S')
    else:
        date_modif = os.path.getmtime(file_path)
        date_modif = datetime.fromtimestamp(date_modif)
    result['date_modif'] = date_modif.strftime('%Y-%m-%d %H:%M:%S')

    orientation = exif_info.get(274, 1)
    result['orient'] = orientation

    return result

def calculate_hash_of_file(filepath):
    ''' Calculates the Hash code of the file.
        The hash code depends on the file content not the name of it.
        So renamed files have the same hash_code.
        If the content of the file is changed the hash code will be
        differ from the original file.'''
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as afile:
        buffer = afile.read()
        hasher.update(buffer)
    return (hasher.hexdigest())

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

def get_photo_data(path, file_name):
    """Sets photo data for the given file."""
    file_path = os.path.join(path, file_name)
    data = {'filename': file_name,
            'source': file_path,
            'dirname': path,
            'uploaded': False,
            'video': is_video_file(file_name),
            'file_size': get_size(file_path)}
    file_info = get_file_info(file_path)
    data.update(file_info)
    return data

def clear_hash_data(path):
    config_path = os.path.join(path, hash_file)
    if is_valid_path(config_path):
        f = open(config_path, 'r+')
        f.truncate(0)

def get_config_options_for_section(path, config, section):
    """Returns options for the givem section from the config file.
        If the file demaged, the content of it will be deleted."""
    result = {}
    config_path = os.path.join(path, hash_file)
    if not is_valid_path(config_path):
        return result
    try:
        config = configparser.ConfigParser()
        config.read(config_path)
        if section not in config.sections():
            return {}
        options = config.options(section)
        for option in options:
            try:
                result[option.lower()] = (config.get(section, option)).lower()
            except Exception as e:
                #Corrupt hash_file -> clear it
                clear_hash_data(path)
    except configparser.MissingSectionHeaderError as mse:
        #Corrupt hash_file -> clear it
        clear_hash_data(path)
    return result

def read_hash_from_config(path):
    """Reads the (filename, hash_code) pairs from config file"""
    config = configparser.ConfigParser()
    return get_config_options_for_section(path, config, hash_photos)

def read_album_from_config(path):
    """Reads amazon albumname for the given path from config file
        If there is no albumname, it returns empty string"""
    config = configparser.ConfigParser({hash_album: ""})
    options = get_config_options_for_section(path, config, hash_album)
    return options.get(hash_album.lower(), "")

def append_to_hash_file(path, section, option, value):
    """"Saves the given option with the given value under
        the given sectioninto the config file.
        If the config file doesn't exist, it creates it.
        If the given section doesn't exist, it adds to the file."""
    config_path = os.path.join(path, hash_file)

    config = configparser.ConfigParser()

    if not is_valid_path(config_path):
        config.add_section(section)
    else:
        config.read(config_path)
        if section not in config.sections():
            config.add_section(section)
    config.set(section, option, value)
    with open(config_path, 'w') as configfile:
        config.write(configfile)

def get_album_name(path, album):
    """ Returns the album_name. The rules:
        First check the config file. If the album is set-it will use it. 
        If not, use the given album parameter """
    album_name = read_album_from_config(path)
    return album_name if album_name else album

def set_selectable(path, data_list, is_valid_album):
   """Marks the uploaded data in the datalist """
   datas = data_list
   if is_valid_album:
       hash_name_pairs = read_hash_from_config(path)
       filenames_from_hash = [file_name.lower() for file_name
           in list(hash_name_pairs)]
       for data in datas:
           if data['filename'].lower() in filenames_from_hash:
               data['uploaded'] = True
   else:
       #the hash_file is corrupt --> clear it
       clear_hash_data(path)
   return datas

class ProgressPercentage(object):
    def __init__(self, file_name):
        self._filename = file_name
        self._size = os.path.getsize(file_name)
        self._lock = threading.Lock()
        self._readed = 0

    def __call__(self, bytes_amount):
        with self._lock:
            self._readed += bytes_amount
            percentage = (self._readed * 100) / self._size
            sys.stdout.write("\r%s  %s / %s  (%.2f%%)" % (
                        self._filename, self._readed, self._size,
                        percentage))
            sys.stdout.flush()

class AmazonUploader():
    def is_valid_bucket(self, album_name):
        result = True
        bucket_name = base_bucket_name + album_name
        try:
            s3.meta.client.head_bucket(Bucket = bucket_name)
        except botocore.client.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                result = False
        return result

    def get_all_photos_data(self, path, album_name):
        """Retruns all data of photos (media files) from the given path"""
        result = []
        media_files = get_media_files(path)
        for file_name in media_files:
            data = get_photo_data(path, file_name)
            result.append(data)
        #check if the album is a valid amazon bucket name
        is_valid_album = self.is_valid_bucket(album_name)
        result = set_selectable(path, result, is_valid_album)
        return result
   
    def append_to_amazon_config(self, photo_data):
        print('OK')

    def upload_photo(self, photo, bucket_name):
        try:
            result =  s3.meta.client.upload_file(Filename = photo['source'], 
                Bucket = bucket_name, Key = photo['filename'],
                ExtraArgs = {'ACL': 'public-read'},
                Callback = ProgressPercentage(photo['source']))
        except ClientError as e:
            return False
        return True

    def update_bucket(self, photos, album_name):
        #update bucket
        amazon_bucket_name = base_bucket_name + album_name
        if photos:
            #checks if the albumname is in configfile. If not, put it in
            append_to_hash_file(
                    photos[0]['dirname'],
                    hash_album,
                    hash_album,
                    album_name)

        for photo in photos:
            #upload photos one by one and add hash to the config file
            hash_of_photo = calculate_hash_of_file(photo['source'])
            print('Upload photo:' + photo['filename'])
            if self.upload_photo(photo, amazon_bucket_name):
                self.append_to_amazon_config(photo)
                append_to_hash_file(photo['dirname'], hash_photos, photo['filename'], hash_of_photo)
            else:
                print('\n Upload failed')

    def create_bucket(self, album_name):
        s3.create_bucket(Bucket = base_bucket_name + album_name)

    def update_or_create_album(self, photos, album_name):
        if not self.is_valid_bucket(album_name):
            #create bucket
            self.create_bucket(album_name)
        self.update_bucket(photos, album_name)

    def upload_all(self, path, album):
        """Upload all media files from the given folder to the given album"""
        album_name = get_album_name(path, album)
        data = self.get_all_photos_data(path, album_name)
        #get the photos needs to be uploaded
        uploadable = [photo for photo in data if photo['uploaded'] == False]
        self.update_or_create_album(uploadable, album_name)
