#!/usr/bin/env python3
# Author: Daniel Escobar


from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from scratchclient import ScratchSession, ScratchIDError
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

def print_intro():
    print("""

       ____             __      __     ___                  __             __       
      / __/__________ _/ /_____/ /    / _ \___ _    _____  / /__  ___ ____/ /__ ____
     _\ \/ __/ __/ _ `/ __/ __/ _ \  / // / _ \ |/|/ / _ \/ / _ \/ _ `/ _  / -_) __/
    /___/\__/_/  \_,_/\__/\__/_//_/ /____/\___/__,__/_//_/_/\___/\_,_/\_,_/\__/_/   

            Author: Daniel Escobar - This project is under MIT License

        If you have any question please contact \033[34mdaniesmor@gsyc.urjc.es                   

    """)


class Tor_Environment():
    def __init__(self):
        self.restarting = False
        self.proxies = {
            'http': 'socks5h://tor_proxy_agent:9050',
            'https': 'socks5h://tor_proxy_agent:9050'
        }

    def check_proxy(self):
        print("Checking Tor proxy status...", end="")
        retries = 1000  # Número de intentos antes de desistir
        while retries > 0:
            try:
                print("\n")
                response = requests.get("https://check.torproject.org", proxies=self.proxies, timeout=1000)
                response.raise_for_status()  # Esto levantará una excepción si hay un error HTTP
                print("ALL OKAY")
                self.restarting = False
                break
            except requests.exceptions.Timeout:
                print("Request timed out. Restarting Tor...")
                self.restart_tor()
                retries -= 1
            except requests.exceptions.RequestException as e:
                print(f"Request failed: {e}. Retrying in 10 secs...")
                time.sleep(10)
                retries -= 1
            except UnicodeDecodeError as e:
                print(f"Error checking proxy: {e}")
        if retries == 0:
            print("Failed to connect after several retries.")
            sys.exit(1)

    def restart_tor(self) -> None:
        """
            This function restarts docker tor container.
        """
        self.restarting = True
        print("RESTARTING TOR ENVIRONMENT, PLEASE WAIT...")
        client = docker.from_env()
        container_name = "tor_proxy_agent"
        try:
            container = client.containers.get(container_name)
            container.restart()
            print(f"Container '{container_name}' resarted successfully.")
            self.check_proxy()
        except docker.errors.NotFound:
            print(f"Container '{container_name}' not found.")
        except Exception as e:
            print(f"An error ocurred: {e}")

class ScratchDownloader:
    def __init__(self, tor_env: Tor_Environment) -> None:
        self.tor_env = tor_env
        # IDs gestion
        self.ids_in_file = set() # This contains all IDs from txt without filter
        self.pending_ids = set() # This will be filtered with the existing dataset
        self.filtered_ids = None # Ammount of IDs presentes
        self.successful_ids = set()
        self.failed_ids = set()
        self.current_id = None

        # Time control
        self.time_offset = 0 # This counts when shows INFO
        self.stop_programmed = False

        # Threads gestion
        self.max_threads = os.cpu_count()
        self.futures = {}

        # Time and Session management
        self.start_time = time.time()
        self.end_time = None
        self.current_session = str(datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

        # Existing dataset management
        self.DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "downloads")
        self.PROJECTS_SUCCESS_DIRNAME = "projects_downloaded"
        self.PROJECTS_FAILED_DIRNAME = "projects_failed"
        self.SUMMARY_DIRNAME = "summaries"
        self.existing_dataset = set()



    def save_projectsb3(self, path_file_temporary, id_project):
        try:
            if not os.path.isdir(self.DOWNLOADS_DIR):
                os.mkdir(self.DOWNLOADS_DIR)
            dir_zips = os.path.join(self.DOWNLOADS_DIR, self.current_session)
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
            #if os.path.exists(temporary_file_name):
                #print(f"File '{temporary_file_name}' already exists.")


            #else:
             #   print(f"no existe {temporary_file_name}")

            file_path = os.path.join(dir_utemp, temporary_file_name)
            try:
                if os.path.exists(file_path):
                    new_file_path = os.path.join(dir_utemp, f'project_{id_project}.json')
                    os.rename(file_path, new_file_path)
                    if os.path.exists(new_file_path):
                        with ZipFile(unique_file_name_for_saving, 'w') as myzip:
                            myzip.write(new_file_path, arcname='project.json')
                else:
                    raise FileNotFoundError(f"El archivo temporal {file_path} no existe en {dir_utemp}")
            except Exception as e:
                print("Ocurrio:",e)
            finally:
                os.chdir(path_project)
        except FileNotFoundError as e:
            thread_name = threading.current_thread().name
            thread_id = threading.get_ident()
            # print(f"Task ID {id_project} is running in thread: {thread_name} with ID: {thread_id}")
            # print(f"Error: {e}")
            raise e
        except Exception as e:
            print(f"An error ocurred: {e}")
            raise e


    def download_scratch_project_from_servers(self, path_project, id_project):
        try:
            scratch_project_inf = ScratchSession().get_project(id_project)
            url_json_scratch = "{}/{}?token={}".format(consts.URL_SCRATCH_SERVER, id_project,
                                                       scratch_project_inf.project_token)
            #print(url_json_scratch)
            path_utemp = os.path.join(os.path.dirname(__file__), "utemp")
            if not os.path.exists(path_utemp):
                os.mkdir(path_utemp)
            path_json_file = os.path.join(path_utemp, str(id_project) + '_new_project.json')
        except requests.exceptions.Timeout:
            if not self.tor_env.restarting:
                self.tor_env.restart_tor()
        except KeyError as e:
            raise ScratchIDError("\033[91m" + f"The project {id_project} does not exists.") from e
        except requests.exceptions.RequestException as e:
            print(f"An error ocurred: {e}")
            raise e
        except UnicodeDecodeError as e:
            print(f"Error downloading project: {e}")

        try:
            response_from_scratch = requests.get(url_json_scratch)
        except HTTPError:
            url_json_scratch = "{}/{}".format(consts.URL_GETSB3, id_project)
            response_from_scratch = urlopen(url_json_scratch)
            path_json_file = os.path.join(os.path.dirname(__file__), "utemp", str(id_project) + '_old_project.json')
        except URLError as e:
            print(f"An error ocurred: {e}")
            traceback.print_exc()
            raise URLError
        except UnicodeDecodeError as e:
            print(f"Error downloading project: {e}")
        except Exception as e:
            print(f"An error ocurred: {e}")
            traceback.print_exc()
            raise e

        try:
            json_string_format = response_from_scratch.content
            resulting_file = open(path_json_file, 'wb')
            resulting_file.write(json_string_format)
            resulting_file.close()
        except IOError:
            traceback.print_exc()
            raise IOError
        except UnicodeDecodeError:
            print(f"Error downloading project: {id_project}")
            traceback.print_exc()

        return path_json_file, scratch_project_inf


    def send_request_getsb3(self, id_project):
        """
        Send request to getsb3 app
        """
        try:
            file_url = '{}{}'.format(id_project, '.sb3')
            path_project = os.path.join(os.path.dirname(__file__))
            path_json_file_temporary, scratch_project_obj = self.download_scratch_project_from_servers(path_project, id_project)
            self.save_projectsb3(path_json_file_temporary, id_project)
        except Exception as e:
            raise e

        return scratch_project_obj


    def create_summary(self):
        os.makedirs(os.path.join(self.DOWNLOADS_DIR, self.current_session, self.SUMMARY_DIRNAME), exist_ok=True)
        with open(os.path.join(self.DOWNLOADS_DIR, self.current_session, self.SUMMARY_DIRNAME, self.PROJECTS_SUCCESS_DIRNAME), "w", errors="replace") as downloaded:
            for id in self.successful_ids:
                downloaded.write(f"{id}\n")
        with open(os.path.join(self.DOWNLOADS_DIR, self.current_session, self.SUMMARY_DIRNAME, self.PROJECTS_FAILED_DIRNAME), "w", errors="replace") as failed:
            for id in self.failed_ids:
                failed.write(f"{id}\n")


    def download_project(self, id_project):
        # sys.stdout.write(f"Downloading project {id_project}... ")
        if not self.tor_env.restarting:
            try:
                scratch_project_obj = self.send_request_getsb3(id_project)
                print("\033[92m" + f"The project {id_project} has been successfully downloaded.")
                self.successful_ids.add(id_project)
            except requests.exceptions.Timeout:
                if not self.tor_env.restarting:
                    self.tor_env.restart_tor()
            except Exception as e:
                self.failed_ids.add(id_project)
                print(e)
                #print("\033[91m" + f"The project {id_project} does not exists.")
            except requests.exceptions.RequestException:
                if not self.tor_env.restarting:
                    self.tor_env.restart_tor()
            except ScratchIDError as e:
                print(e)
            except UnicodeDecodeError as e:
                print(f"Error downloading sb3 info: {e}")
            return True
        else:
            return False


    def calc_rate(self) -> float:
        self.time_offset = 0
        end_time = time.time()
        elapsed_time = end_time - self.start_time
        project_rate = len(self.successful_ids) / elapsed_time
        print(f"\033[1;33mDOWNLOAD RATE: {project_rate} projects/seg\033[0m")
        print(f"There are {len(self.successful_ids)} projects downloaded")
        print(f"There are {len(self.pending_ids)} projects in pending list")
        if self.stop_programmed: print("\033[35m"+f"STOP PROGRAMMED: still {len(self.futures)} to download"+"\033[0m")
        return round(project_rate, 2)

    def show_intro(self):
        message = """
        We are going to start to download, this is the summary:
        - {} IDs from txt IDs file.
        - {} existing sb3 in downloads directory.
        
        There are {} projects from the txt file previously downloaded.
        Taking into the previews sb3 in downloads directory there are {} IDs proposed to download.
        """.format(len(self.ids_in_file),
                   len(self.existing_dataset),
                   len(self.ids_in_file)-len(self.pending_ids),
                   len(self.pending_ids))

        print(message)

    def add_futures(self):
        while len(self.futures) < self.max_threads:
            if not self.pending_ids:
                break
            if self.pending_ids: self.current_id = self.pending_ids.pop()
            if self.current_id not in self.existing_dataset:
                self.time_offset += 1
                self.futures[executor.submit(self.download_project, self.current_id)] = self.current_id

    def download_projects_in_cache(self):
        self.max_threads = os.cpu_count()

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_threads) as executor:

            while len(self.futures) < self.max_threads:
                if not self.pending_ids: break
                self.current_id = self.pending_ids.pop()
                if self.current_id is None:
                    break
                if self.current_id not in self.existing_dataset:
                    self.futures[executor.submit(self.download_project, self.current_id)] = self.current_id

            while self.futures:
                if self.time_offset >= 50: self.calc_rate()
                futures_copy = list(self.futures)
                for future in concurrent.futures.as_completed(futures_copy):
                    try:
                        future_status = future.result()
                        if future_status:
                            self.futures.pop(future)
                            self.time_offset += 1
                            while len(self.futures) < self.max_threads:
                                if not self.pending_ids: break
                                self.current_id = self.pending_ids.pop()
                                if self.current_id not in self.existing_dataset:
                                    self.futures[executor.submit(self.download_project, self.current_id)] = self.current_id
                    except requests.exceptions.SSLError:
                        if not self.tor_env.restarting:
                            self.tor_env.restart_tor()
                    except Exception as exc:
                        traceback.print_exc()
                        print(f"\033[91m Project generated an exception: {exc}")
                    except KeyboardInterrupt:
                        print("\nCtrl+C detected. Stopping the downloader gracefully...")
            self.futures.clear()
        self.show_summary()

    def load_existing_dataset(self):
        duplicate_count = 0  # Contador para duplicados
        seen_items = set()  # Conjunto auxiliar para detectar duplicados

        for name in os.listdir(self.DOWNLOADS_DIR):
            for dataset_file_name in [self.PROJECTS_SUCCESS_DIRNAME, self.PROJECTS_FAILED_DIRNAME]:
                full_dataset_path = os.path.join(self.DOWNLOADS_DIR, name, "summaries", dataset_file_name)
                if os.path.isfile(full_dataset_path):
                    with open(full_dataset_path, "r", errors="replace") as dataset_file:
                        for line in dataset_file:
                            item = line.strip()
                            if item in seen_items:
                                print(f"Duplicate found: {item}")
                                duplicate_count += 1
                            else:
                                seen_items.add(item)
                            self.existing_dataset.add(item)
        self.sync_pending_existing()


    def sync_pending_existing(self):
        self.pending_ids = self.ids_in_file.copy()
        self.pending_ids.difference_update(self.existing_dataset)


    def read_ids_file(self, ids_file) -> None:
        with open(ids_file, 'rb') as f:
            for line in f:
                try:
                    id = line.decode('utf-8').strip()
                    self.ids_in_file.add(id)
                except UnicodeDecodeError as e:
                    print(f"Error en línea {i}: {e}")


    def show_summary(self):
        self.create_summary()
        self.end_time = time.time()
        elapsed_time = self.end_time - self.start_time

        print(F""" 
        ###############################################################
        ##
        ##   SESSION {self.current_session} SUMMARY
        ##   - {len(self.successful_ids)} projects downloaded.
        ##   - {len(self.failed_ids)} projects failed.
        ##   - It tooks {elapsed_time} seconds.
        ##      
        ##   Projects downloaded are located in downloades dir.
        ##   For more info see summaries directory. Thanks for use.
        ##
        #################################################################
        """)
        sys.exit(0)


    def handle_exit(self, signum=None, frame=None):
        print("STOPING RECIEVE, FINISHING DOWNLOADS IN CACHE")
        print(f"There are {len(self.futures)} projects pending.")
        self.pending_ids = set()
        self.stop_programmed = True


def main() -> None:
    print_intro()
    tor_env = Tor_Environment()
    tor_env.check_proxy()
    scratch_downloader = ScratchDownloader(tor_env)
    signal.signal(signal.SIGINT, scratch_downloader.handle_exit)
    scratch_downloader.read_ids_file("./ids_file.txt")
    scratch_downloader.load_existing_dataset()
    scratch_downloader.show_intro()
    scratch_downloader.download_projects_in_cache()
    scratch_downloader.handle_exit()


if __name__ == "__main__":
    main()