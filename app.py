#!/usr/bin/env python
__author__ = "NothingCtrl (Duong Bao Thang)"
__license__ = "GPL"
__version__ = "1.0.1"
__email__ = "thang@camratus.com"

import os
import thread
import time
import logging
import smtplib
import json
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import datetime
from subprocess import check_output
import sys
import ntpath

# https://github.com/google/google-api-python-client/issues/299, not work?
logging.getLogger('googleapicliet.discovery_cache').setLevel(logging.ERROR)

"""
Upload file to GDrive using GDrive API and python library PyDrive 
with multiple thread support.
"""


def read_app_settings():
    """
    Read app setting file app_settings.json
    :return: dict
    """

    settings = {
        "email_address": None,
        "email_password": None,
        "email_smtp_address": None,
        "email_smtp_port": None,
        "email_smtp_tls": False,
        "email_to_address": None,
        "gdrive_parent_folder": None,
        "delete_source_file_after_upload": False,
        "upload_source_folders": None,
        "filter_pattern": None,
        "filter_min_file_age": None,  # minimum age of file to filter, in second, ex: 2592000 = 30 days
        "compress_password": None
    }

    dir_path = os.path.dirname(os.path.realpath(__file__))
    json_path = dir_path + '/app_settings.json'

    if os.path.isfile(json_path):
        with open(json_path, 'r') as json_file:
            settings = json.load(json_file)
    return settings


app_settings = read_app_settings()

# list folders have files to upload
folders = app_settings['upload_source_folders']


# ======================================================


def upload_one_to_gdrive(drive, file_path, thread_id):
    """
    Upload one file
    :param thread_id:
    :param drive: GoogleDrive
    :param file_path:
    :return:
    """
    filename = os.path.basename(file_path)
    config = {'title': filename}
    # id: is folder_id of google drive can get in URL https://drive.google.com/drive/u/2/folders/0Bw_M4RyCyVQTYzFHRjZycWh3Nmc
    if app_settings['gdrive_parent_folder']:
        config['parents'] = [{"kind": "drive#fileLink", "id": app_settings['gdrive_parent_folder']}]
    file1 = drive.CreateFile(config)
    # todo: check file size cause pydrive throw error when upload file zero byte
    file1.SetContentFile(file_path)  # Set content of the file from given string.
    file1.Upload()
    write_log('[%d] Created file %s with mimeType %s' % (thread_id, file1['title'], file1['mimeType']))


def thread_upload_gdrive(drive, files_list, compress_list, thread_id, track_thread):
    compress_password = app_settings['compress_password'] and app_settings['compress_password'] or None

    if not compress_password:
        if files_list:
            for item in files_list:
                try:
                    files_list.remove(item)
                    write_log("[{}] --- Going to upload file {} ---".format(thread_id, item))
                    upload_one_to_gdrive(drive, item, thread_id)
                    write_log("[{1}] Upload done for file: {0}".format(item, thread_id))
                    time.sleep(1)
                    thread_upload_gdrive(drive, files_list, compress_list, thread_id, track_thread)
                except Exception, e:
                    write_log("[%d] Error when upload file %s, exception message: \n%s\n" % (thread_id, item, str(e)))
                    pass
        else:
            track_thread[thread_id] = True
            write_log("[%d] Thread finished" % thread_id)
    else:
        if compress_list or not track_thread[4]:
            if compress_list:
                for item in compress_list:
                    try:
                        compress_list.remove(item)
                        write_log("[{}] --- Going to upload file {} ---".format(thread_id, item))
                        upload_one_to_gdrive(drive, item, thread_id)
                        write_log("[{1}] Upload done for file: {0}".format(item, thread_id))
                        time.sleep(1)
                        thread_upload_gdrive(drive, files_list, compress_list, thread_id, track_thread)
                    except Exception, e:
                        write_log(
                            "[%d] Error when upload file %s, exception message: \n%s\n" % (thread_id, item, str(e)))
                        pass
            else:
                write_log("[%d] wait 15s for compress file..." % thread_id)
                time.sleep(15)
                thread_upload_gdrive(drive, files_list, compress_list, thread_id, track_thread)
        else:
            track_thread[thread_id] = True
            write_log("[%d] Thread finished" % thread_id)


def write_log(log_msg):
    """
    Write log to a file
    :param log_msg:
    :return:
    """
    debug = False
    today = datetime.date.today()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(dir_path)
    if not os.path.isdir('logs'):
        os.mkdir('logs')
    if debug:
        print "[DEBUG] %s" % log_msg
    else:
        logging.basicConfig(filename=dir_path + '/logs/app_log_' + str(today) + '.log', level=logging.DEBUG)
        log_msg = " " + str(datetime.datetime.now()) + " ::: " + log_msg
        logging.info(log_msg)


def send_email(subject, body, to_address=None):
    """
    Send email to admin report error
    :param to_address:
    :param subject:
    :param body:
    :return:
    """

    if app_settings['email_address'] and app_settings['email_password'] and app_settings['email_smtp_address'] \
            and app_settings['email_smtp_port'] and app_settings['email_smtp_tls']:

        toaddrs = to_address and to_address or app_settings['email_to_address']

        if toaddrs:
            msg = "\r\n".join([
                "From: %s" % app_settings['email_address'],
                "To: %s" % toaddrs,
                "Subject: %s" % subject,
                "",
                "%s" % body
            ])
            server = smtplib.SMTP("{}:{}".format(app_settings['email_smtp_address'], app_settings['email_smtp_port']))
            server.ehlo()
            if app_settings['email_smtp_tls']:
                server.starttls()
            server.login(app_settings['email_address'], app_settings['email_password'])
            server.sendmail(app_settings['email_address'], toaddrs, msg)
            server.quit()


def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)


def thread_compress_file(files_list, compress_list, thread_id, track_thread):
    compress_password = app_settings['compress_password'] and app_settings['compress_password'] or None
    if compress_password and files_list:
        for item in files_list:
            # compress file with password, then delete original
            filename = item
            if os.name == 'nt':
                filename += ".rar"
                check_output("rar a \"{}\" \"{}\" -p{} -df -ep -r".format(filename, item, compress_password), shell=True).decode()
            else:
                filename += ".zip"
                # cd to upload folder to bypass folder structure in zip file
                check_output("cd {}; zip -P {} -r \"{}\" \"{}\"".
                             format(os.path.dirname(os.path.abspath(item)), compress_password, path_leaf(filename), path_leaf(item)), shell=True).decode()
                os.remove(item)
            write_log("Compressed file %s and deleted source" % item)
            compress_list.append(filename)

    track_thread[thread_id] = True
    write_log("[%d] Thread finished" % thread_id)


def app_run():
    write_log("--------- App start --------- ")

    """
    Authentication with GDrive
    """
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # Creates local webserver and auto handles authentication.

    drive = GoogleDrive(gauth)

    files_list = []
    compress_list = []

    # pattern: use for filter files with pattern in file name,
    # example pattern = '.zip' to filter file have .zip in the name, set = None if not use.
    pattern = app_settings['filter_pattern'] and app_settings['filter_pattern'] or None
    filter_min_file_age = app_settings['filter_min_file_age'] and int(app_settings['filter_min_file_age']) or None
    run_time = time.time()

    if folders:
        for f in folders:
            files = os.listdir(u"{}".format(f))
            for file_name in files:
                full_filepath = "{}/{}".format(f, file_name)
                if not pattern or pattern in file_name:
                    if not filter_min_file_age or run_time - os.path.getmtime(full_filepath) >= filter_min_file_age:
                        files_list.append(full_filepath)

    list_files_to_delete = files_list[:]
    write_log("--- Total file to upload: %d" % len(files_list))

    compress_password = app_settings['compress_password'] and app_settings['compress_password'] or None
    write_log("--- Compress file with password: %s" % (compress_password and 'Yes' or 'No'))

    track_thread = {1: False, 2: False, 3: False, 4: False}

    """
        Upload with three thread (three files at the same time)
    """
    for i in range(1, 4):
        thread.start_new_thread(thread_upload_gdrive, (drive, files_list, compress_list, i, track_thread,))
        write_log("[%d] Thread start..." % i)
        time.sleep(1)

    if compress_password:
        thread.start_new_thread(thread_compress_file, (files_list, compress_list, 4, track_thread,))
        write_log("[4] Thread start...")
    else:
        track_thread[4] = True
        write_log("[4] Thread finished")

    while not track_thread[1] or not track_thread[2] or not track_thread[3] or not track_thread[4]:
        pass

    # delete uploaded file when done
    if app_settings['delete_source_file_after_upload']:
        for item in list_files_to_delete:
            filename = compress_password and (item + (os.name == 'nt' and ".rar" or ".zip")) or item
            os.remove(filename)
            write_log("Deleted file %s" % filename)

    write_log("--------- App stop --------- ")

# run main function
app_run()

try:
    sys.stdout.close()
except:
    pass
try:
    sys.stderr.close()
except:
    pass

