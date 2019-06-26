from amazonUploader import AmazonUploader
import os
import argparse

parser = argparse.ArgumentParser(description = 'Uploade to amazon')
parser.add_argument('-album', type = str, help = 'Album name')
args = parser.parse_args()

def getFolder():
    return os.getcwd()

def getAlbum():
    """Get the album name for photos - get from argument list or calculate from the folder name"""
    return args.album if args.album else os.path.basename(getFolder())

#def is_valid_path(path):
#    """Checks if the given path is valid or not"""
#    return os.path.exists(path)

album = getAlbum() 

def main():
    uploader = AmazonUploader()
    uploader.upload_all(getFolder(), getAlbum())
    
if __name__ == "__main__":
    main()
