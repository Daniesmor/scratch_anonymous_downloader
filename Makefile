<<<<<<< HEAD
=======
ENV_FILE = PARAMS
>>>>>>> 965d8604da90a5eb72e7686867143c18ad520666
# make start IDSPATH=PATH
requirements:
	pip install -r requirements.txt

build:
	docker-compose build --no-cache --progress=plain

start:
<<<<<<< HEAD
=======
	@echo "AMOUNT=$(AMOUNT)" > $(ENV_FILE) 
	@echo "QUERY=$(QUERY)" > $(ENV_FILE) 
	@echo "MODE=$(MODE)" > $(ENV_FILE) 
	@echo "LANGUAGE=$(LANGUAGE)" > $(ENV_FILE) 
>>>>>>> 965d8604da90a5eb72e7686867143c18ad520666
	docker-compose up


stop:
	docker kill --signal="SIGINT" scratch_downloader
#docker-compose down
<<<<<<< HEAD
=======

>>>>>>> 965d8604da90a5eb72e7686867143c18ad520666

