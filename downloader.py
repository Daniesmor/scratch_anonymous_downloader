from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from scratchclient import ScratchSession
import consts_scratch as consts
import json
import traceback
import argparse
import os
import time
import threading
from datetime import datetime 
from zipfile import ZipFile, BadZipfile
import uuid
import requests
import docker
import concurrent.futures
import random
import sys
import signal
import threading
from query_list import QUERY_LIST
import logging

logging.basicConfig(level=logging.INFO)

stop_program = False
write_query_lock = threading.Lock()

CURR_ID=1106864352
def handle_exit():
    end_time = time.time()
    elapsed_time = end_time - START_TIME


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
    sys.exit(0)

def handle_stop_signal(signum, frame):
    global stop_program
    stop_program = True
    print("\nCtrl+Z detected. Stopping the program...")

#signal.signal(signal.SIGTSTP, handle_stop_signal)
signal.signal(signal.SIGINT, handle_stop_signal)
#signal.signal(signal.SIGTERM, handle_stop_signal)  

SUMMARY_DIR_NAME = "summaries"
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "downloads")
PROJECTS_SUCCESS = "projects_downloaded"
PROJECTS_FAILED = "projects_failed"
PROJECTS_DOWNLOADED = 0
PROJECTS_NO_DOWNLOADED = 0
SIMULTANEOUS_THREADS = 3500000
SESSION = str(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
DATASET_CSV_PATH = os.path.join(DOWNLOADS_DIR, SESSION, "dataset.csv")
OFFSETS_USED = set()
CURR_SESSION_PROJECTS = set()
CURRENT_OFFSET = 0
ANALYZED_IDS = set()
RESTARTING = False
START_TIME = time.time()

analyzed_ids_lock = threading.Lock()
summaries_ids_lock = threading.Lock()


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

parser.add_argument('--amount', type=str, help='Amount of projects to download', default=0)
parser.add_argument('--query', type=str, help='Keywords to search, all projects by default.', default='*')
parser.add_argument('--mode', type=str, help='popular (default), or trending', default='popular')
parser.add_argument('--language', type=str, help='Specific language, en (default)', default='en')

args = parser.parse_args()

args.amount = args.amount if args.amount else 0
args.query = args.query if args.query else '*'
print("QUERY:", args.query)
args.mode = args.mode if args.mode else 'popular'
args.language = args.language if args.language else 'en'
#print(f'Query: {args.query }')

#print(f"We are going to download the IDs contained in {args.amount}.")

def send_request_getsb3(id_project):
    """
    Send request to getsb3 app
    """
    file_url = '{}{}'.format(id_project, '.sb3')
    path_project = os.path.join(os.path.dirname(__file__))
    path_json_file_temporary, scratch_project_obj = download_scratch_project_from_servers(path_project, id_project)
    save_projectsb3(path_json_file_temporary, id_project)
    
    return scratch_project_obj
        

def create_csv():
    dir_zips = os.path.join(DOWNLOADS_DIR, SESSION)
    if not os.path.isdir(dir_zips):
        os.makedirs(os.path.join(DOWNLOADS_DIR, SESSION), exist_ok=True)
    with open(DATASET_CSV_PATH, "w") as csv_file:
        line = f"Title, Project ID, Author, Creation date, Modified date, Remix parent id, Remix root id\n"
        csv_file.write(line)

def save_csv(project):
    with open(DATASET_CSV_PATH, "a") as csv_file:
        project_title = str(project.title).replace(",", "")
        author = str(project.author).replace(",", "")
        line = f"{project_title},{project.id},{author},{project.creation_date},{project.modified_date},{project.remix_parent},{project.remix_root}\n"
        csv_file.write(line)


def download_scratch_project_from_servers(path_project, id_project):
    global RESTARTING
    try:
        scratch_project_inf = ScratchSession().get_project(id_project)
        url_json_scratch = "{}/{}?token={}".format(consts.URL_SCRATCH_SERVER, id_project, scratch_project_inf.project_token)
        path_utemp = os.path.join(os.path.dirname(__file__),"utemp")
        if not os.path.exists(path_utemp):
            os.mkdir(path_utemp)
        path_json_file = os.path.join(path_utemp, str(id_project) + '_new_project.json')
    except requests.exceptions.Timeout:
        if not RESTARTING:
            restart_tor_environment()
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
        raise URLError
    except Exception as e:
        traceback.print_exc()
        raise e

    try:
        json_string_format = response_from_scratch.read()
        json_data = json.loads(json_string_format)
        resulting_file = open(path_json_file, 'wb')
        resulting_file.write(json_string_format)
        resulting_file.close()
    except IOError:
        traceback.print_exc()
        raise IOError

    return path_json_file, scratch_project_inf


def save_projectsb3(path_file_temporary, id_project):
    try:
        if not os.path.isdir(DOWNLOADS_DIR):
            os.mkdir(DOWNLOADS_DIR)
        dir_zips = os.path.join(DOWNLOADS_DIR, SESSION)
        if not os.path.isdir(dir_zips):
            os.mkdir(dir_zips)

        unique_file_name_for_saving = os.path.join(dir_zips, f"{id_project}.sb3")

        dir_utemp = os.path.dirname(path_file_temporary)
        path_project = os.path.dirname(os.path.dirname(__file__))

        if '_new_project.json' in path_file_temporary:
            ext_project = '_new_project.json'
        else:
            ext_project = '_old_project.json'

        temporary_file_name = f"{id_project}{ext_project}"

        os.chdir(dir_utemp)
        try:
            if os.path.exists(temporary_file_name):
                os.rename(temporary_file_name, f'project_{id_project}.json')
                if os.path.exists(f'project_{id_project}.json'):
                    with ZipFile(unique_file_name_for_saving, 'w') as myzip:
                        myzip.write(f'project_{id_project}.json', arcname='project.json')
            else:
                raise FileNotFoundError(f"El archivo temporal {temporary_file_name} no existe en {dir_utemp}")
        finally:
            os.chdir(path_project)  
    except FileNotFoundError as e:
        thread_name = threading.current_thread().name
        thread_id = threading.get_ident()
        #print(f"Task ID {id_project} is running in thread: {thread_name} with ID: {thread_id}")
        #print(f"Error: {e}")
        raise e
    except Exception as e:
        print(f"An error ocurred: {e}")
        raise e
    

def spinner(id_project):
    global PROJECTS_DOWNLOADED, PROJECTS_NO_DOWNLOADED, RESTARTING
    #sys.stdout.write(f"Downloading project {id_project}... ")
    if not RESTARTING:
        try:
            scratch_project_obj = send_request_getsb3(id_project)
            print("\033[92m" + f"The project {id_project} has been successfully downloaded.")
            PROJECTS_DOWNLOADED += 1
            save_csv(scratch_project_obj)
            log_successful(id_project, True)    
        except requests.exceptions.Timeout:
            if not RESTARTING:
                restart_tor_environment() 
        except Exception as e:
            PROJECTS_NO_DOWNLOADED += 1
            print("\033[91m" + f"The project {id_project} does not exists.")
            log_successful(id_project, False)
        return True
    else:
        return False

        
def create_summary():
    os.makedirs(os.path.join(DOWNLOADS_DIR, SESSION, SUMMARY_DIR_NAME), exist_ok=True)
    with open(os.path.join(DOWNLOADS_DIR, SESSION, SUMMARY_DIR_NAME, PROJECTS_SUCCESS), "w") as downloaded:
        pass        
    with open(os.path.join(DOWNLOADS_DIR, SESSION, SUMMARY_DIR_NAME, PROJECTS_FAILED), "w") as failed:
        pass
        

def log_successful(project_id, downloaded):
    with summaries_ids_lock:
        CURR_SESSION_PROJECTS.add(str(project_id).strip())
        #print("CURR_SESSION_PROJECT:", len(CURR_SESSION_PROJECTS))
        if downloaded:
            summary_file = os.path.join(DOWNLOADS_DIR, SESSION, SUMMARY_DIR_NAME, PROJECTS_SUCCESS)
        else:
            summary_file = os.path.join(DOWNLOADS_DIR, SESSION, SUMMARY_DIR_NAME, PROJECTS_FAILED)
        with open(summary_file, 'a') as summary:
            summary.write(str(project_id) + "\n")

def check_proxy():
    global RESTARTING
    print("Checking Tor proxy status...", end="")
    try:
        print("\n")
        response = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=10)
        response.raise_for_status()  # Esto levantará una excepción si hay un error HTTP
        print("ALL OKAY")
        RESTARTING = False
        #print("Success:", response.json())  # Si la solicitud fue exitosa, muestra la respuesta
    except requests.exceptions.Timeout:
        print("Request timed out. Restarting Tor...")
        restart_tor_environment() 
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}. Retrying in 10 secs...")
        time.sleep(10)
        check_proxy()

def print_downloded_projects():
    global START_TIME, PROJECTS_DOWNLOADED
    while True:
        
        end_time = time.time()
        elapsed_time = end_time - START_TIME
        project_vel = PROJECTS_DOWNLOADED / elapsed_time
        logging.info(f"\033[94mPROJECTS DOWNLOADED: {PROJECTS_DOWNLOADED} RATE: {round(project_vel, 2)} pr/sec\033[0m")
        time.sleep(10)

def generate_offset():
    curr_offset = random.randint(0, 9980)
    while True:
        curr_offset = random.randint(0, 9980)
        if curr_offset not in OFFSETS_USED:
            OFFSETS_USED.add(curr_offset)
            return curr_offset

def generate_mode():
    modes = ['popular', 'trending']
    curr_mode_idx = random.randint(0, 1)
    return modes[curr_mode_idx]

def generate_lan_code():
    language_codes = [
    "en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko", "ru", 
    "ar", "hi", "nl", "sv", "fi", "no", "da", "pl", "el", "tr", 
    "he", "uk", "cs", "hu", "ro", "bg", "hr", "sk", "sl", "lt", 
    "lv", "et", "is", "ga", "mt", "cy", "sq", "sr", "mk", "ms", 
    "id", "th", "vi", "bn", "ta", "te", "ml", "kn", "gu", "mr", 
    "pa", "ur", "fa", "sw", "am", "hy", "az", "eu", "be", "ka", 
    "km", "ky", "lo", "mn", "my", "ne", "si", "uz", "tt", "tk", 
    "vo", "wa", "yi", "zu"]
    random_language = random.choice(language_codes)
    return random_language


def sync_existing_ids():
    global ANALYZED_IDS
    try:
        with open("./analized_ids", "r") as anal_ids: 
            for line in anal_ids:
                id = line.strip()
                if id not in ANALYZED_IDS:
                    ANALYZED_IDS.add(id) 
    except FileNotFoundError:
        pass

def write_curr_id(id):
    found = False
    with analyzed_ids_lock:
        with open("./analized_ids", "a+") as anal_ids: 
            print(f"Writing id {id} in analized id file.")
            anal_ids.write(f"{id}\n")  
    

def extract_ids(existing_dataset) -> list:
    """
        Store 100 IDs
    """
    global CURR_ID, RESTARTING
    selected_ids = set() 
    try:
        while len(selected_ids) < 1000:
            selected_ids.add(CURR_ID)
            CURR_ID-=1
    except requests.exceptions.Timeout:
        if not RESTARTING:
            restart_tor_environment() 
    except Exception as e:
        print(f"Catched error in extract_ids: {e}")
    return list(selected_ids)

def load_existing_dataset():
    existing_dataset = set()
    duplicate_count = 0  # Contador para duplicados
    seen_items = set()  # Conjunto auxiliar para detectar duplicados
    
    for name in os.listdir(DOWNLOADS_DIR):
        for dataset_file_name in ["projects_downloaded", "projects_failed"]:
            full_dataset_path = os.path.join(DOWNLOADS_DIR, name, "summaries", dataset_file_name)
            if os.path.isfile(full_dataset_path):
                with open(full_dataset_path, "r") as dataset_file:
                    for line in dataset_file:
                        item = str(line).strip()
                        if item in seen_items:
                            print(f"Duplicate found: {item}")
                            duplicate_count += 1
                        else:
                            seen_items.add(item)
                        existing_dataset.add(item)
    
    #print(f"Total unique items downloaded: {len(existing_dataset)}")
    if duplicate_count != 0:
        print(f"Total duplicates found: {duplicate_count}")
    return existing_dataset


def get_projects():
    """
    Get 40 project IDs
    """
    global stop_program
    projects_ids = []
    existing_dataset = load_existing_dataset()
    check_interval = 9000  
    iteration_counter = 0 
    
    download_projects_threads(existing_dataset)
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = []

        while not stop_program:
            print("CURR QUERY:", QUERY_LIST[0])
            #check_proxy()  # Call your proxy check function
            for _ in range(SIMULTANEOUS_THREADS):
                futures.append(executor.submit(extract_ids, existing_dataset))
            for future in concurrent.futures.as_completed(futures):
                try:
                    extracted_ids = future.result()
                    if extracted_ids:
                        #print("We are going to download:", extracted_ids)
                        
                        print("\033[94mPROJECTS DOWNLOADED:", PROJECTS_DOWNLOADED)
                except requests.exceptions.SSLError:
                    restart_tor_environment()
                except Exception as exc:
                    traceback.print_exc()
                    print(f"\033[91m Project generated an exception: {exc}")
                except KeyboardInterrupt:
                    print("\nCtrl+C detected. Stopping the downloader gracefully...")
                    stop_program = True
            futures.clear()
    """
    handle_exit()
    

def download_projects_threads(existing_dataset):
    max_threads = os.cpu_count()

    global CURR_ID, RESTARTING, stop_program
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = {}
        
        while CURR_ID not in existing_dataset and len(futures) < max_threads:
            futures[executor.submit(spinner, CURR_ID)] = CURR_ID
            CURR_ID -= 1

        for future in concurrent.futures.as_completed(futures):
            try:
                future_status = future.result()
                if not future_status:
                    project_id = futures.pop(future)
                    if not stop_program:
                        if CURR_ID not in existing_dataset:
                            futures[executor.submit(spinner, CURR_ID)] = CURR_ID
                        CURR_ID -= 1
            except requests.exceptions.SSLError:
                if not RESTARTING:
                    restart_tor_environment()
            except Exception as exc:
                traceback.print_exc()
                print(f"\033[91m Project generated an exception: {exc}")
            except KeyboardInterrupt:
                print("\nCtrl+C detected. Stopping the downloader gracefully...")
                stop_program = True
        
        futures.clear()
        
def restart_tor_environment():
    global RESTARTING
    """
    This function restarts docker tor container.
    """
    RESTARTING = True
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

if __name__ == "__main__":
    

    t = threading.Thread(target=print_downloded_projects)
    t.daemon = True 
    t.start()

    create_csv()
    create_summary()
    check_proxy()
    get_projects()
    total= 0

    handle_exit(None, None)


