#!/usr/bin/env python
__author__ = "NothingCtrl (Duong Bao Thang)"
__license__ = "GPL"
__version__ = "2.0.0"
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
import shutil

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
        "delete_source_file": False,
        "delete_compress_file": True,
        "upload_source_folders": [],
        "filter_pattern": [],
        "filter_min_file_age": None,  # minimum age of file to filter, in second, ex: 2592000 = 30 days
        "compress_password": None,
        "max_time_retry_upload_fail": 100,
        "print_log": False,
    }

    dir_path = os.path.dirname(os.path.realpath(__file__))
    json_path = dir_path + '/app_settings.json'

    if os.path.isfile(json_path):
        with open(json_path, 'r') as json_file:
            settings = json.load(json_file)
    return settings


app_settings = read_app_settings()
app_settings['total_file'] = 0
app_settings['uploaded'] = 0
app_settings['fail_count'] = 0

# list folders have files to upload
folders = app_settings['upload_source_folders']
# list compress files need delete after upload
need_delete_files = []

# ======================================================


def upload_one_to_gdrive(drive, file_path, thread_id):
    """
    Upload one file
    :param thread_id:
    :param drive: GoogleDrive
    :param file_path:
    :return:
    """
    try:
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
        return True
    except Exception, e:
        write_log("[{}] Upload file {} failed, error messages:\n{}".format(thread_id, file_path, str(e)))
        app_settings['fail_count'] += 1
        return False


def thread_upload_gdrive(drive, files_list, compress_list, thread_id, track_thread):
    compress_password = app_settings['compress_password'] and app_settings['compress_password'] or None

    if compress_password:
        list_upload = compress_list
    else:
        list_upload = files_list

    if list_upload or not track_thread[4]:
        if list_upload:
            item = list_upload[0]
            list_upload.remove(item)
            app_settings['uploaded'] += 1
            write_log("[{}] --- Going to upload file: {}".format(thread_id, item))
            write_log("[{}] Remaining files: {}".format(thread_id,
                                                        app_settings['total_file'] - app_settings['uploaded']))

            if upload_one_to_gdrive(drive, item, thread_id):
                write_log("[{}] Upload done for file: {}".format(thread_id, item))
                if (compress_password and app_settings['delete_compress_file']) or (
                            not compress_password and app_settings['delete_source_file']):
                    try:
                        time.sleep(2)
                        os.remove(item)
                        write_log("[{}] Delete file: {}".format(thread_id, item))
                    except Exception, e:
                        write_log(
                            "[{}] Failed when delete file {}, messages: {}, will try later...".format(thread_id, item, str(e)))
                        need_delete_files.append(item)
                        pass
            else:
                write_log("[{}] Upload file {} failed, try again later...".format(thread_id, item))
                list_upload.append(item)
                app_settings['uploaded'] -= 1

            time.sleep(1)
            if app_settings['fail_count'] > app_settings['max_time_retry_upload_fail']:
                track_thread[thread_id] = True
                write_log("--- [%d] Thread finished due to upload fail count reached... ---" % thread_id)
            else:
                thread_upload_gdrive(drive, files_list, compress_list, thread_id, track_thread)

        else:
            write_log("[%d] wait 15s for compress file..." % thread_id)
            time.sleep(15)
            thread_upload_gdrive(drive, files_list, compress_list, thread_id, track_thread)
    else:
        track_thread[thread_id] = True
        write_log("--- [%d] Thread finished ---" % thread_id)


def thread_compress_file(files_list, compress_list, thread_id, track_thread):
    compress_password = app_settings['compress_password'] and app_settings['compress_password'] or None
    today = datetime.date.strftime(datetime.date.today(), '%Y-%m-%d')
    if compress_password and files_list:
        for item in files_list:
            while len(compress_list) > 6:
                write_log("[%s] Wait 30s due to compress list > 6..." % thread_id)
                time.sleep(30)
            try:
                filename = "{}_date_{}{}".format(item, today, os.name == 'nt' and ".rar" or ".zip")
                if os.name == 'nt':
                    # -m2 = compress fast
                    rar_ops = " -ep -r -m2"
                    if app_settings['delete_source_file']:
                        rar_ops = " -df -ep -r -m2"
                    check_output("rar a \"{}\" \"{}\" -p{}{}".format(filename, item, compress_password, rar_ops),
                                 shell=True).decode('utf-8')
                else:
                    # cd to upload folder to bypass folder structure in zip file
                    check_output("cd {}; zip -P {} -r \"{}\" \"{}\"".
                                 format(os.path.dirname(os.path.abspath(item)), compress_password, path_leaf(filename),
                                        path_leaf(item)), shell=True).decode('utf-8')
                    if app_settings['delete_source_file']:
                        if not os.path.isdir(item):
                            os.remove(item)
                        else:
                            shutil.rmtree(item)
                        write_log("[%d] Delete source file/folder: %s" % (thread_id, item))
                write_log("[%d] Compressed file %s done" % (thread_id, item))
                compress_list.append(filename)
            except Exception, e:
                write_log("[%d] Error when compress file %s, error messages: \n%s\n" % (thread_id, item, str(e)))
                pass

    track_thread[thread_id] = True
    write_log("[%d] Thread finished" % thread_id)


def write_log(log_msg):
    """
    Write log to a file
    :param log_msg:
    :return:
    """
    today = datetime.date.today()
    dir_path = os.path.dirname(os.path.realpath(__file__))
    os.chdir(dir_path)
    if not os.path.isdir('logs'):
        os.mkdir('logs')
    logging.basicConfig(filename=dir_path + '/logs/app_log_' + str(today) + '.log', level=logging.DEBUG)
    log_msg = " " + str(datetime.datetime.now()) + " ::: " + log_msg
    logging.info(log_msg)
    if app_settings['print_log']:
        print log_msg


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


def is_pattern_in_filename(pattern, path):
    """
    Check filename have string in pattern
    :param pattern: list
    :param path: str
    :return:
    """
    path = path_leaf(path)
    for p in pattern:
        if p in path:
            return True
    return False


def getlist():
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # Creates local webserver and auto handles authentication.

    drive = GoogleDrive(gauth)
    file_list = drive.ListFile({'q': "'{}' in parents and trashed=false".format(app_settings['gdrive_parent_folder'])}).GetList()
    return file_list


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
                if not pattern or is_pattern_in_filename(pattern, file_name):
                    if not filter_min_file_age or run_time - os.path.getmtime(full_filepath) >= filter_min_file_age:
                        files_list.append(full_filepath)

    app_settings['total_file'] = len(files_list)
    compress_password = app_settings['compress_password'] and app_settings['compress_password'] or None

    write_log("--- Total file to upload: %d" % app_settings['total_file'])
    write_log("--- Compress file with password: %s" % (compress_password and 'Yes' or 'No'))
    write_log("--- Delete source file/folder: %s" % (app_settings['delete_source_file'] and 'Yes' or 'No'))
    write_log("--- Delete compress file: %s" % (app_settings['delete_compress_file'] and 'Yes' or 'No'))

    track_thread = {1: False, 2: False, 3: False, 4: False}

    """
        Upload with three thread (three files at the same time)
    """
    for i in range(1, 4):
        thread.start_new_thread(thread_upload_gdrive, (drive, files_list, compress_list, i, track_thread,))
        write_log("[%d] Thread start..." % i)
        time.sleep(3)

    if compress_password:
        thread.start_new_thread(thread_compress_file, (files_list, compress_list, 4, track_thread,))
        write_log("[4] Thread start...")
    else:
        track_thread[4] = True
        write_log("[4] Thread finished")

    while not track_thread[1] or not track_thread[2] or not track_thread[3] or not track_thread[4]:
        pass

    # delete compress file when done
    if need_delete_files:
        for item in need_delete_files:
            os.remove(item)
            write_log("Deleted file %s" % item)
    time.sleep(1)
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
