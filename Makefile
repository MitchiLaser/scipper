all:
	python setup.py sdist bdist_wheel

clean:
	rm -rf build
	rm -rf dist
	rm -rf src/scpi_whisperer.egg-info 

upload: all
	twine upload dist/*

# to set up the venv: run `make venv`
venv:
	bash ./setup_venv.sh

mr-propper: clean
	rm -rf venv/