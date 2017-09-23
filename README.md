## PyDrive Auto Upload Demo APP
This application using library [PyDrive](https://pythonhosted.org/PyDrive/) for upload file to GDrive (Google Drive)  
`pip install pydrive`

### Feature
Upload file to GDrive with file compress files/folders support (only compress when have set value for `compress_password`), able to filter file by name or modified date (file age).

### How to
* First of all, you need enable [Google Drive API](https://console.developers.google.com/apis/api/drive.googleapis.com), and create an __OAuth client ID__  type _Web application_ for using in this app, then put _Client ID, Client secret_ to file `settings.yaml`.
* Compress app: On Windows, using `WinRar`, on Linux\Ubuntu, using `Zip` (WinRar need execute able from CMD, example, you can execute command: `rar <do-something>`). 
* Edit file `app_settings.json` to adapt settings your need:
    * `upload_source_folders`: source folders where store files or folders to upload.
    * `filter_pattern`: list patterns to filter file you want upload, example ["test1", "test2"]: will filter only file or folder have test1 **or** test2 in file name
    * `filter_min_file_age`: the minimum age of file in second, example set value to 2592000 filter file older than 30 days
    * `delete_source_file`: if true (default = false), after file compress, it will be delete source file or folder.
    * `delete_compress_file`: if true (default = true), after file uploaded, it will be delete compress file.
* Files for upload must not contain any space in the filename.
* Run `python app.py`, a log file will create in `logs/app_run_date.log` for logging.
* First time run, you need auth this app with GDrive via browser, file `client_secrets.json` and `credentials.json` create for saving credential data.
