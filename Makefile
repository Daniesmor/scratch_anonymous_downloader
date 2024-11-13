ENV_FILE = PARAMS
# make start IDSPATH=PATH
requirements:
	pip install -r requirements.txt

build:
	docker-compose build

start:
	@echo "AMOUNT=$(AMOUNT)" > $(ENV_FILE) 
	@echo "QUERY=$(QUERY)" > $(ENV_FILE) 
	@echo "MODE=$(MODE)" > $(ENV_FILE) 
	@echo "LANGUAGE=$(LANGUAGE)" > $(ENV_FILE) 
	docker-compose up


stop:
	docker-compose down


