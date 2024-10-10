# Massive Scratch Project Downloader v1.0
If you have any question please contact **daniesmor@gsyc.urjc.es**

This program allows you to download a massive amount of projects from the Scratch projects repository. You only have yo enter an initial Scratch project ID and the amount of projects that you want to download. The program will start download all
Scratch projects availabe (if the ID exist) starting at the initial ID entered until complete the amount entered at first.

*Parameter:*
- IDENTIFIER (INT value)
- AMOUNT (INT value)


## Deploy

### Requirements:
- Docker
- Docker Compose

WARNING: The program has been ONLY tested with Ubunti Linux so if you use Windows it may not works correct. 

### Instructions:

1. Clone this repository: `git clone https://github.com/Daniesmor/scratch_anonymous_downloader.git`.
2. Enter the repo directory cloned `cd scratch_anonymous_downloader`.
3. Exec `make build`
4. Exec `make start IDENTIFIER=INSERT_INTEGER AMOUNT=INSERT_INTEGER`

I.e. `make start IDENTIFIER=754492222 AMOUNT=10`: This instruction will download the first 10 projects above the Scratch project ID 754492222 (include).

