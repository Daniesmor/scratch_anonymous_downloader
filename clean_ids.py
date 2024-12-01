all_ids = set()
with open('./pending_ids', 'r') as ids_file:
    for line in ids_file:
        project_id = line.strip()
        all_ids.add(project_id)

with open('./summaries/2024-11-08_00-03-52/projects_downloaded', 'r') as projects_downloaded:
    for line in projects_downloaded:
        project_id = line.strip()
        all_ids.discard(project_id)  # Removes the item if it exists, does nothing if not

with open('./summaries/2024-11-08_00-03-52/projects_failed', 'r') as projects_non_downloaded:
    for line in projects_non_downloaded:
        project_id = line.strip()
        all_ids.discard(project_id)

with open('./pending_ids', 'w') as pendings_ids:
    for project_id in all_ids:
        pendings_ids.write(project_id + '\n')
