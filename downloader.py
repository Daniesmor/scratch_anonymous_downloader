from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from scratchclient import ScratchSession
import consts_scratch as consts
import json
import traceback
import argparse
import os
import sys
import time
import threading
from datetime import datetime 
from zipfile import ZipFile, BadZipfile
import uuid
import requests
import docker
import concurrent.futures

SUMMARY_DIR = os.path.join(os.path.dirname(__file__), "summaries")
PROJECTS_SUCCESS = "projects_downloaded"
PROJECTS_FAILED = "projects_failed"
PROJECTS_DOWNLOADED = 0
PROJECTS_NO_DOWNLOADED = 0
SIMULTANEOUS_THREADS = 10
SESSION = str(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))


proxies = {
    'http': 'socks5h://tor_proxy:9050',
    'https': 'socks5h://tor_proxy:9050'
}

print("""
                                                                                                                                                 
   ____             __      __     ___                  __             __       
  / __/__________ _/ /_____/ /    / _ \___ _    _____  / /__  ___ ____/ /__ ____
 _\ \/ __/ __/ _ `/ __/ __/ _ \  / // / _ \ |/|/ / _ \/ / _ \/ _ `/ _  / -_) __/
/___/\__/_/  \_,_/\__/\__/_//_/ /____/\___/__,__/_//_/_/\___/\_,_/\_,_/\__/_/   
                                                                                
        Author: Daniel Escobar - This project is under MIT License

    If you have any question please contact \033[34mdaniesmor@gsyc.urjc.es                   
                                                                                                                                                                                                                                                                           
""")


parser = argparse.ArgumentParser(description='An scratch project downloader')

parser.add_argument('--amount', type=int, help='Amount of projects to download', required=True)
parser.add_argument('--query', type=str, help='Keywords to search, all projects by default.', required=False, default='*')
parser.add_argument('--mode', type=str, help='popular (default), or trending', required=False, default='popular')
parser.add_argument('--language', type=str, help='Specific language, en (default)', required=False, default='en')

args = parser.parse_args()

print(f"We are going to download the IDs contained in {args.amount}.")

def send_request_getsb3(id_project):
    """
    Send request to getsb3 app
    """

    file_url = '{}{}'.format(id_project, '.sb3')
    path_project = os.path.join(os.path.dirname(__file__))
    path_json_file_temporary = download_scratch_project_from_servers(path_project, id_project)
    save_projectsb3(path_json_file_temporary, id_project)
    

def download_scratch_project_from_servers(path_project, id_project):
    try:
        scratch_project_inf = ScratchSession().get_project(id_project)
        url_json_scratch = "{}/{}?token={}".format(consts.URL_SCRATCH_SERVER, id_project, scratch_project_inf.project_token)
        path_utemp = os.path.join(os.path.dirname(__file__),"utemp")
        if not os.path.exists(path_utemp):
            os.mkdir(path_utemp)
        path_json_file = os.path.join(path_utemp, str(id_project) + '_new_project.json')
    except KeyError:
        raise KeyError

    try:
        response_from_scratch = urlopen(url_json_scratch)
    except HTTPError:
        url_json_scratch = "{}/{}".format(consts.URL_GETSB3, id_project)
        response_from_scratch = urlopen(url_json_scratch)
        path_json_file = os.path.join(os.path.dirname(__file__),"utemp",str(id_project) + '_old_project.json')
    except URLError:
        traceback.print_exc()
    except:
        traceback.print_exc()

    try:
        json_string_format = response_from_scratch.read()
        json_data = json.loads(json_string_format)
        resulting_file = open(path_json_file, 'wb')
        resulting_file.write(json_string_format)
        resulting_file.close()
    except IOError as e:
        pass

    return path_json_file


def save_projectsb3(path_file_temporary, id_project):
    downloads_dir = os.path.join(os.path.dirname(__file__), "downloads")
    if not os.path.isdir(downloads_dir):
        os.mkdir(downloads_dir)
    dir_zips = os.path.join(downloads_dir, SESSION)
    if not os.path.isdir(dir_zips):
        os.mkdir(dir_zips)

    unique_file_name_for_saving = os.path.join(dir_zips, str(id_project) + ".sb3")

    dir_utemp = path_file_temporary.split(str(id_project))[0].encode('utf-8')
    path_project = os.path.dirname(os.path.dirname(__file__))

    if '_new_project.json' in path_file_temporary:
        ext_project = '_new_project.json'
    else:
        ext_project = '_old_project.json'

    temporary_file_name = str(id_project) + ext_project

    os.chdir(dir_utemp)

    try:
        if os.path.exists(temporary_file_name):
            os.rename(temporary_file_name, 'project.json')
            with ZipFile(unique_file_name_for_saving, 'w') as myzip:
                myzip.write('project.json')
            os.remove('project.json')
        else:
            raise FileNotFoundError(f"Temporal file {temporary_file_name} does not exists in {dir_utemp}")
    finally:
        os.chdir(path_project)


def spinner(id_project):
    global PROJECTS_DOWNLOADED, PROJECTS_NO_DOWNLOADED
    #sys.stdout.write(f"Downloading project {id_project}... ")
    try:
        send_request_getsb3(id_project)
        print("\033[92m" + f"The project {id_project} has been successfully downloaded.")
        PROJECTS_DOWNLOADED += 1
        log_successful(id_project, True)     
    except Exception as e:
        PROJECTS_NO_DOWNLOADED += 1
        print("\033[91m" + f"The project {id_project} does not exists.")
        log_successful(id_project, False)

def create_summary():
    summaries_dir = os.path.join(os.path.dirname(__file__), SUMMARY_DIR)
    if not os.path.isdir(summaries_dir):
        os.mkdir(summaries_dir)
    os.mkdir(os.path.join(SUMMARY_DIR, SESSION))
    with open(os.path.join(SUMMARY_DIR, SESSION, PROJECTS_SUCCESS), "w") as downloaded:
        pass        
    with open(os.path.join(SUMMARY_DIR, SESSION, PROJECTS_FAILED), "w") as failed:
        pass
        

def log_successful(project_id, downloaded):
    if downloaded:
        summary_file = os.path.join(SUMMARY_DIR, SESSION, PROJECTS_SUCCESS)
    else:
        summary_file = os.path.join(SUMMARY_DIR, SESSION, PROJECTS_FAILED)
    with open(summary_file, 'a') as summary:
        summary.write(str(project_id) + "\n")

def check_proxy():
    try:
        requests.get("https://httpbin.org/ip", proxies=proxies, timeout=5)
    except:
        time.sleep(10)
        check_proxy()

def extract_ids(projects_array: list) -> list:
    return [project["id"] for project in projects_array]

def get_projects():
    """
    Get 40 projects IDs
    """
    projects_ids = []
    
    while len(projects_ids) < args.amount:
        print("Current ids list:", projects_ids)
        try:
            request_url = f"https://api.scratch.mit.edu/explore/projects?q={args.query}&mode={args.mode}&language={args.language}"
            projects_array = requests.get(request_url, proxies=proxies, timeout=5)
            print(projects_array)
            projects_ids.extends(extract_ids(projects_array))
        except HTTPError:
            restart_tor_environment()
        
def restart_tor_environment():
    """
    This function restarts docker tor container.
    """
    print("RESTARTING TOR ENVIRONMENT, PLEASE WAIT...")
    client = docker.from_env()
    container_name = "tor_proxy"
    try:
        container = client.containers.get(container_name)
        container.restart()
        print(f"Container '{container_name}' resarted successfully.")
        check_proxy()
    except docker.errors.NotFound:
        print(f"Container '{container_name}' not found.")
    except Exception as e:
        print(f"An error ocurred: {e}") 

start_time = time.time()
create_summary()
check_proxy()
project_ids = get_projects()



with concurrent.futures.ThreadPoolExecutor(max_workers=SIMULTANEOUS_THREADS) as executor:
    futures = {executor.submit(spinner, project_id): project_id for project_id in project_ids}
    
    for future in concurrent.futures.as_completed(futures):
        project_id = futures[future]
        try:
            future.result()
            project_ids.remove(project_id)
        except requests.exceptions.SSLError:
            print("RESTARTING TOR ENVIRONMENT, PLEASE WAIT...")
            client = docker.from_env()
            container_name = "tor_proxy"
            try:
                container = client.containers.get(container_name)
                container.restart()
                print(f"Container '{container_name}' resarted successfully.")
                check_proxy()
            except docker.errors.NotFound:
                print(f"Container '{container_name}' not found.")
            except Exception as e:
                print(f"An error ocurred: {e}")
        except Exception as exc:
            print(f"\033[91m Project {project_id} generated an exception: {exc}")

with open(f'pending_{args.idspath}', 'w') as pending_file:
    for project_id in project_ids:
        pending_file.write(project_id) 


end_time = time.time()
elapsed_time = end_time - start_time


print(F""" 
###############################################################
##
##   SESSION {SESSION} SUMMARY
##   - {PROJECTS_DOWNLOADED} projects downloaded.
##   - {PROJECTS_NO_DOWNLOADED} projects failed.
##   - It tooks {elapsed_time} seconds.
##      
##   Projects downloaded are located in downloades dir.
##   For more info see summaries directory. Thanks for use.
##
#################################################################
""")