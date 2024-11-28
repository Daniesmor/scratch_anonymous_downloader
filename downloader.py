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

stop_program = False

def handle_exit():
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
SIMULTANEOUS_THREADS = 18
SESSION = str(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
DATASET_CSV_PATH = os.path.join(DOWNLOADS_DIR, SESSION, "dataset.csv")
OFFSETS_USED = set()
CURR_SESSION_PROJECTS = set()
CURRENT_OFFSET = 0

QUERY_LIST = [
    # Entretenimiento y cultura pop
    "film", "tv", "anime", "meme", "cartoon", "superhero", "music", "movie", 
    "comedy", "dance", "celebrity", "magic",

    # Juegos y géneros específicos
    "rpg", "strategy", "puzzle", "tycoon", "sandbox", "runner", "battle", 
    "shooter", "adventure", "arcade", "platformer", "clicker", "maze", "pong", 
    "survival", "space", "minecraft", "zombie", "tower defense", "speedrun",

    # Educación y aprendizaje
    "math", "history", "geography", "language", "calculator", "flashcards", 
    "coding", "science", "physics", "spelling", "chemistry", "biology", 
    "logic", "quiz", "tutorials", "learning tools", "test preparation", 

    # Exploración y creatividad
    "drawing", "design", "building", "architecture", "art", "creative", 
    "sketch", "model", "virtual world", "house design", "3D modeling", 

    # Simulaciones
    "physics", "simulation", "economy", "weather", "machine", "robotics", 
    "flight simulator", "car simulator", "city builder", "ecosystem", 
    "agriculture", "traffic",

    # Proyectos interactivos
    "poll", "survey", "test", "interactive story", "choose your own adventure", 
    "decision making", "reaction test", "interactive game", 

    # Social y colaborativo
    "chat", "messaging", "remix", "collaboration", "forum", "community", 
    "friend", "team project",

    # Estaciones y celebraciones
    "holiday", "Christmas", "Halloween", "season", "Easter", "Valentine", 
    "New Year", "birthday", "festival", "summer", "winter", "fall", "spring", 

    # Naturaleza y exploración
    "animals", "ocean", "forest", "space exploration", "dinosaur", "zoo", 
    "planet", "solar system", "wildlife", "nature walk", 

    # Temas adicionales populares
    "car", "robot", "ai", "machine learning", "sports", "football", 
    "basketball", "racing", "bike", "boat", "treasure hunt", "pirates", 
    "spy", "ninja", "castle", "knight", "dragon", "fantasy", 

    # Cultura y emociones
    "love", "friendship", "family", "dreams", "fun", "happiness", "sadness", 
    "hope", "kindness", "teamwork", "advice", 

    # Subgéneros y temáticas específicas
    "horror", "mystery", "detective", "crime", "alien", "future", "time travel", 
    "steampunk", "cyberpunk", "underwater", "medieval", "war", "outer space"
]

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
    try:
        scratch_project_inf = ScratchSession().get_project(id_project)
        url_json_scratch = "{}/{}?token={}".format(consts.URL_SCRATCH_SERVER, id_project, scratch_project_inf.project_token)
        path_utemp = os.path.join(os.path.dirname(__file__),"utemp")
        if not os.path.exists(path_utemp):
            os.mkdir(path_utemp)
        path_json_file = os.path.join(path_utemp, str(id_project) + '_new_project.json')
    except requests.exceptions.Timeout:
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
    global PROJECTS_DOWNLOADED, PROJECTS_NO_DOWNLOADED
    #sys.stdout.write(f"Downloading project {id_project}... ")
    try:
        scratch_project_obj = send_request_getsb3(id_project)
        print("\033[92m" + f"The project {id_project} has been successfully downloaded.")
        PROJECTS_DOWNLOADED += 1
        save_csv(scratch_project_obj)
        log_successful(id_project, True)    
    except requests.exceptions.Timeout:
        restart_tor_environment() 
    except Exception as e:
        PROJECTS_NO_DOWNLOADED += 1
        print("\033[91m" + f"The project {id_project} does not exists.")
        log_successful(id_project, False)

        
def create_summary():
    os.makedirs(os.path.join(DOWNLOADS_DIR, SESSION, SUMMARY_DIR_NAME), exist_ok=True)
    with open(os.path.join(DOWNLOADS_DIR, SESSION, SUMMARY_DIR_NAME, PROJECTS_SUCCESS), "w") as downloaded:
        pass        
    with open(os.path.join(DOWNLOADS_DIR, SESSION, SUMMARY_DIR_NAME, PROJECTS_FAILED), "w") as failed:
        pass
        

def log_successful(project_id, downloaded):
    lock = threading.Lock()
    with lock:
        #CURR_SESSION_PROJECTS.add(str(project_id).strip())
        #print("CURR_SESSION_PROJECT:", len(CURR_SESSION_PROJECTS))
        if downloaded:
            summary_file = os.path.join(DOWNLOADS_DIR, SESSION, SUMMARY_DIR_NAME, PROJECTS_SUCCESS)
        else:
            summary_file = os.path.join(DOWNLOADS_DIR, SESSION, SUMMARY_DIR_NAME, PROJECTS_FAILED)
        with open(summary_file, 'a') as summary:
            summary.write(str(project_id) + "\n")

def check_proxy():
    print("Checking Tor proxy status...", end="")
    try:
        print("\n")
        response = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=5)
        response.raise_for_status()  # Esto levantará una excepción si hay un error HTTP
        #print("Success:", response.json())  # Si la solicitud fue exitosa, muestra la respuesta
    except requests.exceptions.Timeout:
        print("Request timed out. Restarting Tor...")
        restart_tor_environment()
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}. Retrying in 10 secs...")
        time.sleep(10)
        check_proxy()

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


def sync_existing_query():
    global QUERY_LIST
    try:
        with open("./analized_queries", "r") as anal_queries: 
            for line in anal_queries:
                query = line.strip()
                if query in QUERY_LIST:
                    QUERY_LIST.remove(query) 
    except FileNotFoundError:
        pass

def write_curr_query(query):
    with open("./analized_queries", "a") as anal_queries: 
        print(f"Writing query {query} in analized queries file.")
        anal_queries.write(f"{query}\n")  




def extract_ids(existing_dataset) -> list:
    global CURRENT_OFFSET
    selected_ids = set() 
    try:
        offset = generate_offset()
        mode = generate_mode()
        language = generate_lan_code()
        query = sync_existing_query()
        request_url = f"https://api.scratch.mit.edu/explore/projects?q={QUERY_LIST[0]}&mode=recent&language={args.language}&limit=40&offset={CURRENT_OFFSET}"
        CURRENT_OFFSET += 30 # Deberia ser 40, pero me siento mas seguro poniendo 30
        if CURRENT_OFFSET > 9890:
            write_curr_query(QUERY_LIST[0])
            CURRENT_OFFSET = 0
        print("CURR_OFFSET:",CURRENT_OFFSET)
        print(request_url)
        projects_array = requests.get(request_url, proxies=proxies, timeout=5).json()

        if projects_array:         
            #existing_dataset = load_existing_dataset()
            #print("RONDA--------------------------------------------------------")              
            for project in projects_array:
                project_id = str(project["id"]).strip()
                #combined_datasets = existing_dataset | CURR_SESSION_PROJECTS
                if project_id not in existing_dataset:
                    if project_id not in CURR_SESSION_PROJECTS:
                        selected_ids.add(project_id)
                        CURR_SESSION_PROJECTS.add(project_id)
                else:
                    print("REPE")
        #print("IDs seleccionadas:", selected_ids)
        #print("MI CURRSESSION:", CURR_SESSION_PROJECTS)
    except requests.exceptions.Timeout:
        restart_tor_environment()

    
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
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=SIMULTANEOUS_THREADS) as executor:
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
                        download_projects_threads(extracted_ids)
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
    handle_exit()
        


def download_projects_threads(project_ids_list):
    with concurrent.futures.ThreadPoolExecutor(max_workers=SIMULTANEOUS_THREADS) as executor:
        futures = {executor.submit(spinner, project_id): project_id for project_id in project_ids_list}
        
        for future in concurrent.futures.as_completed(futures):
            project_id = futures[future]
            try:
                curr_project_path = os.path.join(DOWNLOADS_DIR, SESSION, f"{project_id}.sb3")
                future.result()
            except requests.exceptions.SSLError:
                restart_tor_environment()
            except Exception as exc:
                traceback.print_exc()
                print(f"\033[91m Project {project_id} generated an exception: {exc}")

        
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

if __name__ == "__main__":
    start_time = time.time()

    create_csv()
    create_summary()
    check_proxy()
    get_projects()
    total= 0

    handle_exit(None, None)


