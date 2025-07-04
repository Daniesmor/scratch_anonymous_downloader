import os
import shutil

"""
This file is to extract all the project inside downloads sessions dir, and create
an unified dataset.
"""

DATASET_PATH = os.path.join(os.getcwd(), "dataset")

def log_project(id):
	downloaded_ids = os.path.join(DATASET_PATH,"raw_ids")
	with open(downloaded_ids, "a+") as down_ids:
		down_ids.write(f"{id}\n")


def log_csv(project_id, curr_sess):
    sess_csv = os.path.join(curr_sess, "dataset.csv")
    downloaded_csv = os.path.join(DATASET_PATH, "dataset.csv")

    if not os.path.isfile(sess_csv):
        print(f"Session CSV {sess_csv} does not exist.")
        return

    curr_line = None
    with open(sess_csv, "r") as session_csv:
        for line in session_csv:
            curr_id = line.split(",")[1].strip()
            if curr_id == project_id:
                curr_line = line
                break  

    if curr_line is None:
        print(f"Project ID {project_id} not found in {sess_csv}.")
        return

    with open(downloaded_csv, "a+") as down_csv:
        print(curr_line)
        down_csv.write(curr_line)

    print(f"Project {project_id} logged to {downloaded_csv}.")
          
          
		
def collect_projects():
    downloads_path = os.path.join(os.getcwd(), "downloads") 
    
    if os.path.isdir(downloads_path):
        for session_dir in os.listdir(downloads_path):
            curr_sess = os.path.join(downloads_path, session_dir)
            summaries_path = os.path.join(curr_sess, "summaries", "projects_downloaded")
            
            if os.path.isfile(summaries_path):
                try:
                    with open(summaries_path, "r") as down_ids:
                        for line in down_ids:
                            project_id = line.strip() 
                            sb3_file_path = os.path.join(curr_sess, f"{project_id}.sb3")
                            
                            if os.path.isfile(sb3_file_path):
                                if not os.path.exists(os.path.join(DATASET_PATH, f"{project_id}.sb3")):
                                    shutil.copy(sb3_file_path, DATASET_PATH)
                                    log_project(project_id)
                                    log_csv(project_id, curr_sess)
                                else:
                                    print(f"Project {project_id} already in dataset.")
                except Exception as e:
                    print(f"Error reading {summaries_path}: {e}")
    else:
        print(f"Directory {downloads_path} does not exist.")	
 		 
def create_dataset_dir():
	if not os.path.exists(DATASET_PATH):
		os.mkdir(DATASET_PATH)

def create_dataset_sum():
	downloaded_ids = os.path.join(DATASET_PATH,"raw_ids")
	dataset_csv = os.path.join(DATASET_PATH, "dataset.csv")
	if not os.path.isfile(downloaded_ids):
		with open(downloaded_ids, "w"):
			pass

	if not os.path.isfile(dataset_csv):
		with open(dataset_csv, "w") as dataset_csv_file:
			dataset_csv_file.write("Title, Project ID, Author, Creation date, Modified date, Remix parent id, Remix root id\n")
	


if __name__ == "__main__":
	create_dataset_dir()
	create_dataset_sum()
	collect_projects()
