import os
import thread
import time
import logging
import smtplib
import json
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import datetime

# https://github.com/google/google-api-python-client/issues/299, not work?
logging.getLogger('googleapicliet.discovery_cache').setLevel(logging.ERROR)

"""
This example application demo how to upload file to GDrive using GDrive API and python library PyDrive 
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
    }

    if os.path.isfile('app_settings.json'):
        with open('app_settings.json', 'r') as json_file:
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


def upload_gdrive(drive, files_list, thread_id, track_thread):
    if files_list:
        for item in files_list:
            try:
                write_log("[{}] --- Going to upload file {} ---".format(thread_id, item))
                files_list.remove(item)
                upload_one_to_gdrive(drive, item, thread_id)
                if app_settings['delete_source_file_after_upload']:
                    os.remove(item)
                    write_log("[{}] Deleted file {}".format(thread_id, item))
                write_log("[{1}] Upload done for file: {0}".format(item, thread_id))
                upload_gdrive(drive, files_list, thread_id, track_thread)
            except:
                write_log("[%d] Error when upload file %s" % (thread_id, item))
                pass
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


def app_run():

    write_log("--------- App start --------- ")

    """
    Authentication with GDrive
    """
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()  # Creates local webserver and auto handles authentication.

    drive = GoogleDrive(gauth)

    files_list = []

    # pattern: use for filter files with pattern in file name,
    # example pattern = '.zip' to filter file have .zip in the name, set = None if not use.
    pattern = len(app_settings['filter_pattern']) > 0 and app_settings['filter_pattern'] or None

    for f in folders:
        files = os.listdir(u"{}".format(f))
        for file_name in files:
            if not pattern or pattern in file_name:
                files_list.append("{}/{}".format(f, file_name))

    """
    Upload with three thread (three files at the same time)
    """
    track_thread = {1: False, 2: False, 3: False}

    thread.start_new_thread(upload_gdrive, (drive, files_list, 1, track_thread,))
    time.sleep(1)
    thread.start_new_thread(upload_gdrive, (drive, files_list, 2, track_thread,))
    time.sleep(1)
    thread.start_new_thread(upload_gdrive, (drive, files_list, 3, track_thread,))

    while not track_thread[1] or not track_thread[2] or not track_thread[3]:
        pass


# run main function
app_run()
