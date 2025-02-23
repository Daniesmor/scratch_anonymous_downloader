# make start IDSPATH=PATH
requirements:
	pip install -r requirements.txt

build:
	docker-compose build --no-cache --progress=plain

start:
	docker-compose up


stop:
	docker kill --signal="SIGINT" scratch_downloader
#docker-compose down

