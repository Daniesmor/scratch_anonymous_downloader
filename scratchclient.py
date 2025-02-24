import requests
import consts_scratch as consts


class Project:

    def __init__(self, json_data):
        #print("esta es la id", json_data)
        self.id = json_data["id"]
        self.title = json_data["title"]

        self.description = json_data["description"] if "description" in json_data else None
        self.instructions = json_data["instructions"] if "instructions" in json_data else None

        self.visible = json_data["visibility"] == "visible"
        self.public = json_data["public"]
        self.comments_allowed = json_data["comments_allowed"]
        self.is_published = json_data["is_published"]
        self.project_token = json_data["project_token"]
        self.author = json_data["author"]["username"]
        self.creation_date = json_data["history"]["created"]
        self.modified_date = json_data["history"]["modified"]
        self.remix_parent = json_data["remix"]["parent"]
        self.remix_root = json_data["remix"]["root"]


class RemixtreeProject:

    def __init__(self, data):
        self.id = data["id"]
        self.author = data["username"]
        self.moderation_status = data["moderation_status"]
        self.title = data["title"]

        self.created_timestamp = data["datetime_created"]["$date"]
        self.last_modified_timestamp = data["mtime"]["$date"]
        self.shared_timestamp = (
            data["datetime_shared"]["$date"] if data["datetime_shared"] else None
        )


class ScratchSession:

    def __init__(self, username=None):
        self.logged_in = False
        self.username = username
        self.csrf_token = None
        
        self.proxies = {
      
            'http': 'socks5h://tor_proxy:9050',
            'https': 'socks5h://tor_proxy:9050'
        }
        
    def get_project(self, project):
        project_id = (project.id if isinstance(project, (RemixtreeProject, Project)) else project)
        #print(requests.get(f'{consts.URL_SCRATCH_API}/{project_id}/', proxies=self.proxies).json())
        scratch_response = requests.get(f'{consts.URL_SCRATCH_API}/{project_id}/', proxies=self.proxies, timeout=5).json()
        return Project(scratch_response)