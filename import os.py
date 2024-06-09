import io
import os
import google.auth
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import PyPDF2
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from PyPDF2 import PdfMerger


# 1. Created the necessary functions: 

def get_credentials():
    """Function that creates user credentials necessary for authorization."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json")
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json")
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


def list_course_id():
    """ 
    Function that ;ists all courses the user has access to, and their id.
    Returns:
        courses_id (dictionary): a dictionary consisting of keys that are
        the name of a course (string), and the value being the id (string)
        of given course.
    """
    courses_id = {}
    creds = get_credentials()
    try:
        service = build("classroom", "v1", credentials=creds) # prepares an API request
        results = service.courses().list(pageSize=10).execute() # api response is stored here
        courses = results.get("courses", []) # extracting wanted info from the api response
        if not courses:
            print("No courses found.")
        else:
            print("Courses:")
            for course in courses:
                print(f'Course ID: {course["id"]}, Course Name: {course["name"]}')
                courses_id[course["name"]] = course["id"]
        return courses_id
    except HttpError as error:
        print(f"An error occurred: {error}")


def class_materials(course_id):
    """
    Function that returns a list of all materials in a given course. 
    Returns:
        materials (dictionary): dictionary consisting of each material 
        found in the course. 
    """
    creds = get_credentials()
    try:
        service = build("classroom", "v1", credentials=creds) # prepares an API request
        results = service.courses().announcements().list(courseId = course_id).execute() # extracting the announcement object
        announcements = results.get("announcements", []) # extracting each announcement id
        materials = [i.get("materials") for i in announcements] # extracting the materials dict
        return materials
    except HttpError as error:
        print(f"An error occurred: {error}")

def create_folder(folder_name):
  """
  Create a folder and prints the folder ID
  Returns:
      (string): id of the created folder.
  """
  creds = get_credentials()
  
  try:
    service = build("drive", "v3", credentials=creds)
    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }

    file = service.files().create(body=file_metadata, fields="id").execute()
    print(f'Folder ID: "{file.get("id")}".')
    return file.get("id")

  except HttpError as error:
    print(f"An error occurred: {error}")
    return None

def copy_file(file_id, copy_title, folder_id):
    """Function that copies a Drive file into a Drive folder."""
    copied_file = {
        'name': copy_title,
        'parents': [folder_id]
    }
    creds = get_credentials()
    try:
        service = build("drive", "v3", credentials=creds) # prepares an API request
        copied_file = service.files().copy(
            fileId=file_id,
            body=copied_file).execute()
        print(f'File copied successfully, new file ID: {copied_file.get("id")})')
        return {'id': copied_file.get('id'), 'title': copied_file.get('name')}
    except HttpError as error:
        print(f'An error occurred: {error}')


def get_file(file_id, file_name):
    """Function that downloads specific file from Google Drive."""
    creds = get_credentials()
    service = build("drive", "v3", credentials=creds) # prepares an API request
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(file_name, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"Downloading {file_name}.")


def pdf_merge(pdf_list, merged_file_name):
    """Function that returns a merged PDF file consisting of a list of PDFs."""
    merger = PdfMerger()
    for pdf in pdf_list:
        merger.append(pdf)
    merger.write(merged_file_name)
    merger.close()


# 2. Executing the goal of gathering specific list of PDF files, then merging them
# and lastly downloading the merged PDF file. 

if __name__ == '__main__':
    course_list = list_course_id()
    time_id = course_list['Czas psychologiczny 2024']
    time_materials = class_materials(time_id)
    files_to_copy = []

    for time_class in time_materials:
        if time_class is not None: 
            for file in time_class:
                if ("Czas" in file['driveFile']['driveFile']['title']) and ("pdf" in file['driveFile']['driveFile']['title']):
                    files_to_copy.append({'id': file['driveFile']['driveFile']['id'], 'title': file['driveFile']['driveFile']['title']})
    
    time_folder_id = create_folder("Czas psychologiczny slajdy")

    file_ids = [file['id'] for file in files_to_copy]
    folder_id = time_folder_id 
    copies = []
    for file_id in file_ids:
        copy_title = file_id
        copies.append(copy_file(file_id, copy_title, folder_id))

    folder_id = time_folder_id
    copy_titles = []

    for copy in copies:
        get_file(copy['id'], copy['title'])
        copy_titles.append(copy['title'])

    merged_slides_name = 'Czas psychologiczny slajdy scalone.pdf'
    pdf_merge(copy_titles, merged_slides_name)
    print(f'Merged PDF saved as {merged_slides_name}.')
