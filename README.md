## PyDrive Auto Upload Demo APP
This application using library [PyDrive](https://pythonhosted.org/PyDrive/) for upload file to GDrive (Google Drive)

### Feature
Upload file to GDrive with file compress support (only compress when have set value for compress_password), able to filter file by name or modified date (file age), option to delete uploaded.

### How to
* First of all, you need enable [Google Drive API](https://console.developers.google.com/apis/api/drive.googleapis.com), and create an __OAuth client ID__  type _Web application_ for using in this app, then put _Client ID, Client secret_ to file `settings.yaml`. 
* On Windows, will using WinRar to compress file, WinRar need execute able from CMD (how: add WinRar install folder to PATH), ex: `rar <do-something>`. On Ubuntu, will using `zip` to compress files
* Edit file `app_settings.json` to adapt settings your need, you can set multiple folders as source folders. `filter_min_file_age` is the minimum age of file in second, example set value to 2592000 filter file older than 30 days
* Config parameter `delete_source_file_after_upload` in `app_settings.json` mean, after file uploaded, it will be delete file in local.
* Files for upload must not contain any space in the filename.
* To upload files, run `python app.py`, a log file will create in `logs/app_run_date.log` for logging.

