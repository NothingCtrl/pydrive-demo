from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import os
import thread
import time

"""
This example application demo how to upload file to GDrive using GDrive API and python library PyDrive 
with multiple thread support.
"""

# list folders have files to upload
folders = ('/path/to/folder/upload',)

# pattern: use for filter files with pattern in file name,
# example pattern = '.zip' to filter file have .zip in the name, set = None if not use.
pattern = None

# delete_when_doen: set to True to delete file after upload
delete_when_done = True

files_list = []
for f in folders:
    files = os.listdir(u"{}".format(f))
    for file_name in files:
        if not pattern or pattern in file_name:
            files_list.append("{}/{}".format(f, file_name))

# ======================================================


def upload_one_to_gdrive(file_path):
    """
    Upload one file
    :param file_path:
    :return:
    """
    filename = os.path.basename(file_path)
    file1 = drive.CreateFile({'title': filename})
    # todo: check file size cause pydrive throw error when upload file zero byte
    file1.SetContentFile(file_path)  # Set content of the file from given string.
    file1.Upload()
    print('Created file %s with mimeType %s' % (file1['title'], file1['mimeType']))


def upload_gdrive(files_list, thread_id, track_thread):
    if files_list:
        for item in files_list:
            try:
                files_list.remove(item)
                upload_one_to_gdrive(item)
                if delete_when_done:
                    os.remove(item)
                print "Upload done for file: %s in thread_id: %d" % (item, thread_id)
                upload_gdrive(files_list, thread_id, track_thread)
            except:
                print "Error when upload file %s" % item
                pass
    else:
        track_thread[thread_id] = True


"""
Authentication with GDrive
"""
gauth = GoogleAuth()
gauth.LocalWebserverAuth()  # Creates local webserver and auto handles authentication.

drive = GoogleDrive(gauth)

"""
Upload with three thread (three files at the same time)
"""
track_thread = {1: False, 2: False, 3: False}

thread.start_new_thread(upload_gdrive, (files_list, 1, track_thread,))
time.sleep(1)
thread.start_new_thread(upload_gdrive, (files_list, 2, track_thread,))
time.sleep(1)
thread.start_new_thread(upload_gdrive, (files_list, 3, track_thread,))

while not track_thread[1] or not track_thread[2] or not track_thread[3]:
    pass
